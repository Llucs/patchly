from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from patchly.config import (
    PATCHLY_DIR,
    WORKSPACE,
    PatchlyConfig,
    load_config,
)
from patchly.llm import PATCHLY_SYSTEM_PROMPT, chat, divider, log as llm_log
from patchly.analyzers import run_analyzers
from patchly.actions import ActionResult
from patchly.context import build_context, list_project_files
from patchly.memory import load_memory, add_decision, add_known_issue
from patchly.risk import score_issue, classify, risk_context as get_risk_context
from patchly.safe_mode import check_safe, SafeModeError
from patchly.web import fetch_safe, extract_urls

REPORTS_DIR = WORKSPACE / PATCHLY_DIR / "reports"
VERIFICATION_MAX_CYCLES = 3


class Agent:
    def __init__(self, config: PatchlyConfig | None = None):
        self.config = config or load_config()
        self.context: dict[str, Any] = {}
        self.memory = load_memory()

    def run(self) -> int:
        divider()
        print(f"  PATCHLY — {self.config.mode.upper()} MODE", flush=True)
        print(f"  Provider: {self.config.provider} | Model: {self.config.model}", flush=True)
        divider()

        llm_log("Building context...")
        self.context = build_context(self.config)
        llm_log(f"Context built: {len(self.context.get('files', []))} files loaded")

        web_content = self._load_web_context()
        memory_context = self.memory.to_context()

        mode = self.config.mode
        llm_log(f"Starting {mode} analysis...")

        if mode == "review":
            results = self._run_review(web_content, memory_context)
        elif mode == "scan":
            results = self._run_scan(memory_context)
        elif mode == "fix":
            results = self._run_fix(web_content, memory_context)
        elif mode == "continuous":
            results = self._run_continuous(memory_context)
        elif mode == "command":
            results = self._run_command(web_content, memory_context)
        elif mode == "resolve":
            results = self._run_resolve(memory_context)
        else:
            llm_log(f"Unknown mode: {mode}")
            return 1

        self._write_report(results)
        for r in results:
            if r.severity in ("error", "warning"):
                self._record_to_memory(r)

        errors = [r for r in results if r.severity == "error"]
        warnings = [r for r in results if r.severity == "warning"]

        if errors:
            llm_log(f"Found {len(errors)} error(s), {len(warnings)} warning(s).")
        elif warnings:
            llm_log(f"No errors, but {len(warnings)} warning(s) found.")
        else:
            llm_log("No issues found.")

        divider()
        return 1 if errors else 0

    def _load_web_context(self) -> str:
        event = self.context.get("event", {})
        bodies = []
        if event.get("issue", {}).get("body"):
            bodies.append(event["issue"]["body"])
        if event.get("comment", {}).get("body"):
            bodies.append(event["comment"]["body"])
        if event.get("pull_request", {}).get("body"):
            bodies.append(event["pull_request"]["body"])

        all_urls = set()
        for body in bodies:
            all_urls.update(extract_urls(body))

        if not all_urls:
            return ""

        llm_log(f"Fetching {len(all_urls)} URL(s) from context...")
        parts = []
        for url in sorted(all_urls):
            result = fetch_safe(url)
            if result:
                llm_log(f"  Fetched: {url}")
                parts.append(f"Content from {url}:\n{result['content'][:3000]}")
            else:
                llm_log(f"  Failed: {url}")

        return "\n\n---\n\n".join(parts) if parts else ""

    def _record_to_memory(self, result: ActionResult) -> None:
        desc = result.description[:200]
        files = result.files or []
        for f in files:
            add_known_issue(result.title[:100], f, result.severity)
        add_decision(
            f"Found issue: {result.title[:100]}",
            f"Severity {result.severity}: {desc[:200]}",
            ", ".join(files) if files else "",
        )

    def _build_system_prompt(self, extra: str = "") -> str:
        base = PATCHLY_SYSTEM_PROMPT
        if extra:
            base += "\n\n## Additional context\n" + extra
        risk = get_risk_context([], "")
        base += "\n\n## Risk rules\n" + risk
        base += "\n\n" + self._output_instructions()
        return base

    def _output_instructions(self) -> str:
        outputs = self.config.outputs
        parts = []
        if outputs.pr_comments:
            parts.append("- Post comments on PRs with findings")
        if outputs.issues:
            parts.append("- Create GitHub issues for actionable problems")
        if outputs.patch_prs:
            parts.append("- Generate fix PRs with patches")
        if outputs.reports:
            parts.append("- Save detailed reports to .patchly/reports/")
        return "## Output modes\n" + "\n".join(parts) if parts else ""

    def _run_review(self, web_context: str, memory_context: str) -> list[ActionResult]:
        event = self.context.get("event", {})
        pr_data = event.get("pull_request", {})
        pr_number = pr_data.get("number")

        if pr_number is None:
            llm_log("No pull request number in event — skipping review")
            return []

        llm_log(f"Reviewing PR #{pr_number}...")

        from patchly.github_client import get_pr_diff, create_comment

        diff = get_pr_diff(pr_number)
        pr_info = {
            "title": pr_data.get("title", ""),
            "body": pr_data.get("body", ""),
            "number": pr_number,
            "diff": diff[:30000] if diff else "",
        }

        extra_parts = []
        if web_context:
            extra_parts.append("## Fetched web content\n" + web_context)
        if memory_context:
            extra_parts.append("## Repository memory\n" + memory_context)

        system = self._build_system_prompt("\n\n".join(extra_parts) if extra_parts else "")

        analysis = chat(
            [
                {
                    "role": "user",
                    "content": (
                        f"Review this pull request #{pr_number}:\n\n"
                        f"Title: {pr_info['title']}\n"
                        f"Description: {pr_info['body']}\n\n"
                        f"--- DIFF ---\n{pr_info['diff']}\n\n"
                        "Analyze for bugs, code quality, architecture impact, "
                        "performance, security, and test coverage. "
                        "Provide specific, actionable feedback with file paths. "
                        "Use sections: ## Summary, ## Issues, ## Suggestions"
                    ),
                }
            ],
            self.config,
            system=system,
        )

        risk_score = score_issue(ActionResult("review", "info", analysis))
        llm_log(f"Risk score: {risk_score} ({classify(risk_score)})")

        if self.config.comment_on_pr:
            try:
                create_comment(pr_number, analysis)
                llm_log("Review comment posted")
            except PermissionError:
                llm_log("Cannot post comment — missing `pull-requests: write` permission")

        return [ActionResult("review", classify(risk_score) if risk_score > 1 else "info", analysis)]

    def _run_scan(self, memory_context: str) -> list[ActionResult]:
        llm_log("Scanning repository for issues...")

        files = list_project_files()
        source_files = [
            f for f in files
            if f.suffix in {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
                ".java", ".rb", ".php", ".c", ".cpp", ".cs",
            }
            and f.stat().st_size > 0
        ]
        llm_log(f"Found {len(source_files)} source files")

        if not source_files:
            llm_log("No source files found — nothing to scan")
            return []

        selected = source_files[:self.config.max_files_per_run * 2]
        llm_log(f"Analyzing {len(selected)} files...")

        results = run_analyzers(selected, self.config)

        errors = [r for r in results if r.severity == "error"]
        warnings = [r for r in results if r.severity == "warning"]
        infos = [r for r in results if r.severity == "info"]

        llm_log(f"Scan complete: {len(errors)} error(s), {len(warnings)} warning(s), {len(infos)} info(s)")

        actionable = errors + warnings
        if actionable and self.config.outputs.issues:
            from patchly.github_client import create_issue

            for r in actionable:
                risk_score = score_issue(r)
                level = classify(risk_score)
                llm_log(f"Issue: {r.title[:80]} (risk: {level})")
                try:
                    create_issue(
                        f"Patchly: {r.title}",
                        f"{r.description}\n\n**Risk:** {level}\n\n```\n{r.detail[:5000]}\n```",
                        [f"{self.config.label_prefix}", r.severity, level],
                    )
                    llm_log(f"  ✓ Issue created")
                except PermissionError:
                    llm_log(f"  ✗ Cannot create issue — need `issues: write` permission")
                except Exception as e:
                    llm_log(f"  ✗ Failed to create issue: {e}")

        return results

    def _run_fix(self, web_context: str, memory_context: str) -> list[ActionResult]:
        llm_log("Fix mode: scanning for issues to fix...")

        scan_results = self._run_scan(memory_context)
        fixable = [r for r in scan_results if r.severity in ("error", "warning") and r.files]
        llm_log(f"Found {len(fixable)} fixable issues")

        results = []
        for issue in fixable:
            risk_score = score_issue(issue)
            level = classify(risk_score)
            llm_log(f"Processing: {issue.title[:80]} (risk: {level}, score: {risk_score})")

            if level == "high":
                llm_log(f"  SKIP — high risk requires human review")
                results.append(ActionResult(
                    "fix", "warning",
                    f"Requires human review: {issue.title} (risk score: {risk_score})",
                ))
                continue

            safe_check = check_safe(issue.files, issue.description, self.config.safe_mode)
            if isinstance(safe_check, str) and self.config.safe_mode.block_destructive_changes:
                llm_log(f"  BLOCKED by safe mode")
                results.append(ActionResult("fix", "warning", f"Blocked by safe mode: {issue.title}"))
                continue

            try:
                fixed = self._fix_with_verification(issue)
                if fixed:
                    results.append(fixed)
            except SafeModeError as e:
                llm_log(f"  Safe mode error: {e}")
                results.append(ActionResult("fix", "error", str(e)))

        return results

    def _fix_with_verification(self, issue: ActionResult) -> ActionResult | None:
        from patchly.modes.fix import _generate_fix, _apply_fix_as_pr

        file_path = issue.files[0]

        for cycle in range(1, VERIFICATION_MAX_CYCLES + 1):
            llm_log(f"  Fix cycle {cycle}/{VERIFICATION_MAX_CYCLES}...")

            fix = _generate_fix(issue, self.config)
            if fix is None:
                llm_log("  No fix generated (content unchanged)")
                return None

            fix_data = json.loads(fix.detail)
            new_content = fix_data.get("new_content", "")

            division = _check_division(new_content, fix_data.get("original_content", ""))
            if division:
                llm_log(f"  Fix too aggressive ({division.lines_removed} lines removed vs {division.lines_added} added), retrying...")
                if cycle < VERIFICATION_MAX_CYCLES:
                    issue.description += f"\n\nPrevious attempt was too aggressive: removed {division.lines_removed} lines, added {division.lines_added}. Be more conservative."
                    continue

            if self.config.outputs.patch_prs:
                pr_url = _apply_fix_as_pr(issue, fix, self.config)
                if pr_url:
                    llm_log(f"  Fix PR created: {pr_url}")
                    add_decision(f"Created fix PR for {issue.title[:60]}", f"PR: {pr_url}", file_path)
                    return ActionResult("fix", "info", f"Fix PR: {pr_url}")
                llm_log("  Failed to create PR, falling back to report")
                return ActionResult("fix", "info", fix.description)

            return fix

        llm_log("  Max verification cycles reached without passing")
        return ActionResult("fix", "warning", f"Could not verify fix for {issue.title} after {VERIFICATION_MAX_CYCLES} attempts")

    def _run_resolve(self, memory_context: str) -> list[ActionResult]:
        llm_log("Resolve mode: fetching open issues...")

        from patchly.github_client import (
            add_labels,
            create_comment,
            list_issues,
            update_issue,
        )

        issues = list_issues(label=self.config.label_prefix, state="open")
        if not issues:
            llm_log("No open issues to resolve")
            return []

        llm_log(f"Found {len(issues)} open issue(s)")
        fixes = []
        results = []

        for issue in issues:
            number = issue["number"]
            title = issue["title"]
            body = issue.get("body", "")
            labels = [l["name"] for l in issue.get("labels", [])]

            if "resolving" in labels or "resolved" in labels:
                llm_log(f"  #{number} — already being processed, skipping")
                continue

            llm_log(f"  #{number}: {title[:80]}")

            try:
                add_labels(number, ["resolving"])
            except PermissionError:
                llm_log(f"  Cannot add label to #{number}")

            analysis = self._analyze_issue(number, title, body, memory_context)
            action = analysis.get("action")

            if action == "fix":
                entry = self._prepare_fix(number, title, analysis)
                if entry:
                    fixes.append(entry)
                results.append(entry[2] if entry else ActionResult("resolve", "info", f"#{number}: skipped"))
            elif action == "close":
                comment = analysis.get("comment", "This issue appears to be resolved.")
                try:
                    create_comment(number, comment)
                    update_issue(number, {"state": "closed"})
                    llm_log(f"  #{number} — closed as resolved")
                except PermissionError:
                    llm_log(f"  Cannot close #{number}")
                results.append(ActionResult("resolve", "info", f"Closed #{number}: {comment[:200]}"))
            else:
                llm_log(f"  #{number} — skipped (action={action})")

        if fixes and self.config.outputs.batch_fix_prs:
            self._apply_batch_fix_pr(fixes, results)
        elif fixes:
            for number, fix, _ in fixes:
                self._apply_individual_fix_pr(number, fix, results)

        llm_log(f"Resolve complete: {len(results)} issue(s) processed")
        return results

    def _prepare_fix(
        self, number: int, title: str, analysis: dict,
    ) -> tuple[int, ActionResult, ActionResult] | None:
        from patchly.modes.fix import _generate_fix
        from patchly.risk import classify, score_issue

        files = analysis.get("files", [])
        if not files:
            llm_log(f"  #{number} — no files identified for fix")
            return None

        issue_result = ActionResult(
            "resolve", "error", analysis.get("description", title), files=files,
        )
        risk_score = score_issue(issue_result)
        level = classify(risk_score)

        if level == "high":
            llm_log(f"  #{number} — high risk, requires human review")
            return None

        fix = _generate_fix(issue_result, self.config)
        if fix is None:
            llm_log(f"  #{number} — fix not generated")
            return None

        result = ActionResult(
            "resolve", "info", f"#{number}: fix generated for {files[0]}",
        )
        return (number, fix, result)

    def _apply_individual_fix_pr(
        self, number: int, fix: ActionResult, results: list[ActionResult],
    ) -> None:
        from patchly.github_client import create_comment
        from patchly.modes.fix import _apply_fix_as_pr

        issue_result = ActionResult("resolve", "info", fix.description)
        pr_url = _apply_fix_as_pr(issue_result, fix, self.config)
        if pr_url:
            try:
                create_comment(
                    number,
                    f"**Fix PR created:** {pr_url}\n\n"
                    f"_This PR was automatically generated by Patchly._",
                )
            except PermissionError:
                pass
            llm_log(f"  #{number} — fix PR: {pr_url}")
            results.append(ActionResult("resolve", "info", f"#{number}: fix PR {pr_url}"))
        else:
            results.append(ActionResult("resolve", "warning", f"#{number}: could not create PR"))

    def _apply_batch_fix_pr(
        self, fixes: list[tuple[int, ActionResult, ActionResult]], results: list[ActionResult],
    ) -> None:
        from patchly.github_client import create_comment, create_pr, get_branch_sha, get_default_branch
        import base64, os, httpx
        from patchly.github_client import API, HEADERS, GITHUB_REPOSITORY

        if not fixes:
            return

        branch_name = f"patchly/batch-fix-{os.urandom(4).hex()}"
        llm_log(f"  Creating batch branch {branch_name}...")

        try:
            main_sha = get_branch_sha(get_default_branch())
        except Exception as e:
            llm_log(f"  Cannot get main SHA: {e}")
            return

        ref_resp = httpx.post(
            f"{API}/repos/{GITHUB_REPOSITORY}/git/refs",
            headers=HEADERS,
            json={"ref": f"refs/heads/{branch_name}", "sha": main_sha},
            timeout=15,
        )
        if ref_resp.status_code not in (200, 201):
            llm_log(f"  Branch creation failed: {ref_resp.status_code}")
            return

        changed_files = []
        for number, fix, _ in fixes:
            try:
                fix_data = json.loads(fix.detail)
            except (json.JSONDecodeError, KeyError):
                continue

            file_path = fix_data.get("file", "")
            new_content = fix_data.get("new_content", "")
            if not file_path or not new_content:
                continue

            try:
                info = httpx.get(
                    f"{API}/repos/{GITHUB_REPOSITORY}/contents/{file_path}",
                    headers=HEADERS, timeout=15,
                )
                current_sha = info.json().get("sha", "") if info.status_code == 200 else ""

                put = httpx.put(
                    f"{API}/repos/{GITHUB_REPOSITORY}/contents/{file_path}",
                    headers=HEADERS,
                    json={
                        "message": f"patchly: fix #{number} - {Path(file_path).name}",
                        "content": base64.b64encode(new_content.encode()).decode(),
                        "sha": current_sha,
                        "branch": branch_name,
                    },
                    timeout=15,
                )
                if put.status_code in (200, 201):
                    changed_files.append(file_path)
                    llm_log(f"  #{number} — {file_path} updated")
            except Exception as e:
                llm_log(f"  #{number} — file write error: {e}")

        if not changed_files:
            llm_log("  No files changed, skipping PR")
            return

        body_lines = [
            "## Automated batch fix by Patchly\n",
        ]
        for number, fix, _ in fixes:
            try:
                fix_data = json.loads(fix.detail)
                file_path = fix_data.get("file", "")
                body_lines.append(f"- #{number}: fix in `{file_path}`")
            except Exception:
                body_lines.append(f"- #{number}")

        try:
            pr = create_pr(
                title=f"Patchly: batch fix ({len(changed_files)} file(s))",
                body="\n".join(body_lines),
                head=branch_name,
            )
            pr_url = pr.get("html_url", "")
        except PermissionError as e:
            llm_log(f"  PR creation failed — insufficient permissions: {e}")
            pr_url = ""
        except Exception as e:
            llm_log(f"  PR creation failed: {e}")
            pr_url = ""

        if pr_url:
            for number, _, _ in fixes:
                try:
                    create_comment(
                        number,
                        f"**Batch fix PR:** {pr_url}\n\n"
                        f"_This fix was included in a batch PR along with other changes._",
                    )
                except PermissionError:
                    pass
            llm_log(f"  Batch PR created: {pr_url}")
            results.append(ActionResult("resolve", "info", f"Batch fix PR: {pr_url}"))
        else:
            llm_log("  PR creation failed")

    def _analyze_issue(
        self, number: int, title: str, body: str, memory_context: str,
    ) -> dict:
        from patchly.llm import chat

        files = list_project_files()
        file_list = "\n".join(
            str(f.relative_to(WORKSPACE))
            for f in files
            if f.suffix in {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".rb", ".php", ".c", ".cpp", ".cs"}
            and f.stat().st_size > 0
        )[:8000]

        prompt = (
            f"Issue #{number}: {title}\n\n"
            f"Description:\n{body[:4000]}\n\n"
            f"Current project files:\n{file_list}\n\n"
            "Analyze this issue and respond with a JSON object:\n"
            '{"action": "fix"|"close"|"skip", "files": ["path1", "path2"], "description": "...", "comment": "..."}\n'
            "- fix: issue still exists and should be fixed\n"
            "- close: issue is already resolved or no longer relevant\n"
            "- skip: unsure or needs human review\n"
            '"files": list of files likely involved (for "fix" action)\n'
            '"description": short technical description of the problem\n'
            '"comment": what to post on the issue\n'
            "Respond with ONLY valid JSON, no markdown."
        )

        system = self._build_system_prompt(memory_context)
        result = chat([{"role": "user", "content": prompt}], self.config, system=system)

        import json as _json
        try:
            return _json.loads(result)
        except (_json.JSONDecodeError, Exception):
            llm_log(f"  Could not parse LLM response for #{number}")
            return {"action": "skip", "comment": "Could not analyze this issue automatically."}

    def _run_continuous(self, memory_context: str) -> list[ActionResult]:
        llm_log("Continuous mode: incremental maintenance...")

        state_file = WORKSPACE / PATCHLY_DIR / "state.json"
        state: dict[str, Any] = {}
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text())
            except (json.JSONDecodeError, OSError):
                state = {}

        last_run = state.get("last_run", "")
        files = list_project_files()
        llm_log(f"Repository has {len(files)} tracked files")

        source_files = [
            f for f in files
            if f.suffix in {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
                ".java", ".rb", ".php", ".c", ".cpp", ".cs",
            }
            and f.stat().st_size > 0
        ]

        last_run_time = 0.0
        if last_run:
            try:
                last_run_time = datetime.fromisoformat(last_run).timestamp()
            except (ValueError, TypeError):
                pass

        changed_files = [
            f for f in source_files
            if f.stat().st_mtime > last_run_time
        ] if last_run_time > 0 else source_files

        if not changed_files:
            llm_log("No changed files since last run")
            return []

        batch = changed_files[:self.config.context_engine.max_files]
        llm_log(f"Processing {len(batch)} files (batch of {len(changed_files)} changed)...")

        for f in batch:
            llm_log(f"  Analyzing: {f}")

        results = run_analyzers(batch, self.config)
        fixable = [r for r in results if r.severity in ("error", "warning") and r.files]

        fix_results = []
        for issue in fixable:
            risk_score = score_issue(issue)
            level = classify(risk_score)
            llm_log(f"Issue in {issue.files[0]}: {issue.title[:60]} (risk: {level})")

            if level == "low" and self.config.outputs.issues:
                from patchly.github_client import create_issue
                create_issue(
                    f"Patchly: {issue.title}",
                    f"{issue.description}\n\n_{'Auto-detected in continuous mode'}_",
                    [self.config.label_prefix, "continuous"],
                )

        state["last_run"] = datetime.now(timezone.utc).isoformat()
        state["files_processed"] = state.get("files_processed", 0) + len(batch)
        state["issues_found"] = state.get("issues_found", 0) + len(fixable)
        (WORKSPACE / PATCHLY_DIR).mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(state, indent=2))

        llm_log(f"Continuous run complete: {len(batch)} files, {len(fixable)} issues")
        return fix_results

    def _run_command(self, web_context: str, memory_context: str) -> list[ActionResult]:
        event = self.context.get("event", {})
        cmd = ""

        comment_body = ""
        if event.get("issue"):
            comment_body = event.get("comment", {}).get("body", "")
        elif event.get("inputs", {}).get("command"):
            comment_body = event["inputs"]["command"]

        for line in comment_body.split("\n"):
            stripped = line.strip().lower()
            if stripped.startswith("/patchly"):
                cmd = stripped[len("/patchly"):].strip()
                break

        llm_log(f"Command: {cmd or 'scan'}")

        if not cmd or cmd in ("scan", "analyze"):
            return self._run_scan(memory_context)

        extra_parts = []
        if web_context:
            extra_parts.append("## Fetched web content\n" + web_context)
        if memory_context:
            extra_parts.append("## Repository memory\n" + memory_context)

        system = self._build_system_prompt("\n\n".join(extra_parts) if extra_parts else "")

        command_prompt = (
            f"Execute this software engineering command on the current repository:\n\n"
            f"Command: {cmd}\n\n"
            f"Repository structure and file contents have been loaded. "
            f"Analyze and perform the requested action. "
            f"If modifications are needed, describe exactly what should change and why."
        )

        files = list_project_files()
        file_list = "\n".join(f.name for f in files[:50])
        command_prompt += f"\n\nProject files:\n{file_list}"

        result = chat([{"role": "user", "content": command_prompt}], self.config, system=system)

        if self.config.comment_on_pr:
            from patchly.github_client import create_comment
            issue_number = (event.get("issue") or {}).get("number")
            if issue_number:
                try:
                    create_comment(issue_number, result)
                    llm_log(f"Response posted to issue #{issue_number}")
                except PermissionError:
                    llm_log("Cannot post comment — missing `pull-requests: write` permission")

        return [ActionResult("command", "info", result)]

    def _write_report(self, results: list[ActionResult]) -> None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).isoformat()
        report = {
            "timestamp": timestamp,
            "mode": self.config.mode,
            "results": [r.to_dict() for r in results],
        }
        path = REPORTS_DIR / f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
        path.write_text(json.dumps(report, indent=2))


class DivisionCheck:
    def __init__(self, lines_removed: int, lines_added: int):
        self.lines_removed = lines_removed
        self.lines_added = lines_added


def _check_division(new_content: str, original_content: str) -> DivisionCheck | None:
    new_lines = new_content.strip().split("\n")
    orig_lines = original_content.strip().split("\n")
    removed = max(0, len(orig_lines) - len(new_lines))
    added = max(0, len(new_lines) - len(orig_lines))
    if added == 0:
        return None
    if removed > len(orig_lines) * 0.5 or removed > added * 3:
        return DivisionCheck(removed, added)
    return None
