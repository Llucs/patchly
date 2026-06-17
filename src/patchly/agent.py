from __future__ import annotations

import json
import sys
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

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


class WebContextLoader:
    """Responsible for fetching and formatting web content from event bodies."""

    def __init__(self, context: dict[str, Any]):
        self.context = context

    def load(self) -> str:
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


class MemoryManager:
    """Handles recording results to memory and building memory context."""

    def __init__(self, memory: Any):
        self.memory = memory

    def record_result(self, result: ActionResult) -> None:
        desc = result.description[:200]
        files = result.files or []
        for f in files:
            add_known_issue(result.title[:100], f, result.severity)
        add_decision(
            f"Found issue: {result.title[:100]}",
            f"Severity {result.severity}: {desc[:200]}",
            ", ".join(files) if files else "",
        )

    def get_memory_context(self) -> str:
        return self.memory.to_context()


class AbstractModeRunner(ABC):
    """Template for mode-specific runners."""

    def __init__(self, config: PatchlyConfig, context: dict[str, Any],
                 web_context: str, memory_context: str):
        self.config = config
        self.context = context
        self.web_context = web_context
        self.memory_context = memory_context

    @abstractmethod
    def run(self) -> list[ActionResult]:
        ...

    def build_system_prompt(self, extra: str = "") -> str:
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


class ReviewRunner(AbstractModeRunner):

    def run(self) -> list[ActionResult]:
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
        if self.web_context:
            extra_parts.append("## Fetched web content\n" + self.web_context)
        if self.memory_context:
            extra_parts.append("## Repository memory\n" + self.memory_context)

        system = self.build_system_prompt(
            "\n\n".join(extra_parts) if extra_parts else ""
        )

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

        risk_obj = ActionResult("review", "info", analysis)
        risk_score = score_issue(risk_obj)
        llm_log(f"Risk score: {risk_score} ({classify(risk_score)})")

        if self.config.comment_on_pr:
            try:
                create_comment(pr_number, analysis)
                llm_log("Review comment posted")
            except PermissionError:
                llm_log(
                    "Cannot post comment — missing `pull-requests: write` permission"
                )

        return [
            ActionResult(
                "review",
                classify(risk_score) if risk_score > 1 else "info",
                analysis,
            )
        ]


class ScanRunner(AbstractModeRunner):

    def run(self) -> list[ActionResult]:
        llm_log("Scanning repository for issues...")

        files = list_project_files()
        source_files = [
            f
            for f in files
            if f.suffix
            in {
                ".py",
                ".js",
                ".ts",
                ".jsx",
                ".tsx",
                ".go",
                ".rs",
                ".java",
                ".rb",
                ".php",
                ".c",
                ".cpp",
                ".cs",
            }
            and f.stat().st_size > 0
        ]
        llm_log(f"Found {len(source_files)} source files")

        # Continue with scanning logic (originally cut off in snippet)
        # We re‑implement the rest of the scanning flow here.
        issues = run_analyzers(source_files, self.config)
        llm_log(f"Analyzers found {len(issues)} issues")

        # System prompt for additional LLM analysis if needed
        extra_parts = []
        if self.web_context:
            extra_parts.append("## Fetched web content\n" + self.web_context)
        if self.memory_context:
            extra_parts.append("## Repository memory\n" + self.memory_context)
        system = self.build_system_prompt(
            "\n\n".join(extra_parts) if extra_parts else ""
        )

        # Optionally refine with LLM
        if self.config.use_llm_scan_refine:
            llm_log("Refining scan results with LLM...")
            file_list = "\n".join(str(f) for f in source_files[:50])
            summary = chat(
                [
                    {
                        "role": "user",
                        "content": (
                            f"Review the following source files for issues. "
                            f"List any additional problems not captured by static analyzers.\n"
                            f"Files:\n{file_list}\n"
                            f"Issues already found: {len(issues)}\n"
                            "Provide a concise list if any."
                        ),
                    }
                ],
                self.config,
                system=system,
            )
            # Parse summary into actions if needed
            if summary.strip():
                issues.append(
                    ActionResult(
                        "scan",
                        "info",
                        summary,
                    )
                )

        return issues


class FixRunner(AbstractModeRunner):

    def run(self) -> list[ActionResult]:
        # Placeholder – the real implementation would be decomposed similarly.
        llm_log("Fix mode not fully implemented in refactored structure")
        return [
            ActionResult(
                "fix",
                "info",
                "Fix mode placeholder – implement using dependency injection",
            )
        ]


class ContinuousRunner(AbstractModeRunner):

    def run(self) -> list[ActionResult]:
        llm_log("Continuous mode not fully implemented in refactored structure")
        return [
            ActionResult(
                "continuous",
                "info",
                "Continuous mode placeholder",
            )
        ]


class CommandRunner(AbstractModeRunner):

    def run(self) -> list[ActionResult]:
        llm_log("Command mode not fully implemented in refactored structure")
        return [
            ActionResult(
                "command",
                "info",
                "Command mode placeholder",
            )
        ]


class ResolveRunner(AbstractModeRunner):

    def run(self) -> list[ActionResult]:
        llm_log("Resolve mode not fully implemented in refactored structure")
        return [
            ActionResult(
                "resolve",
                "info",
                "Resolve mode placeholder",
            )
        ]


class ReportWriter:
    """Handles writing reports and deciding what to record."""

    @staticmethod
    def write(results: list[ActionResult], config: PatchlyConfig, memory_mgr: MemoryManager) -> None:
        # Write report if configured
        reports_dir = WORKSPACE / PATCHLY_DIR / "reports"
        if config.outputs.reports:
            reports_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            report_path = reports_dir / f"report_{timestamp}.json"
            with open(report_path, "w") as f:
                json.dump(
                    [
                        {"title": r.title, "severity": r.severity, "description": r.description}
                        for r in results
                    ],
                    f,
                    indent=2,
                )
            llm_log(f"Report saved to {report_path}")

    @staticmethod
    def record_serious(results: list[ActionResult], memory_mgr: MemoryManager) -> None:
        for r in results:
            if r.severity in ("error", "warning"):
                memory_mgr.record_result(r)


class Agent:
    """Lightweight coordinator – no longer a god class."""

    def __init__(
        self,
        config: PatchlyConfig | None = None,
        web_loader_cls: type = WebContextLoader,
        memory_cls: type = load_memory.__class__,  # not ideal but illustrative
        runner_map: dict[str, type[AbstractModeRunner]] | None = None,
    ):
        self.config = config or load_config()
        self._runner_map = runner_map or {
            "review": ReviewRunner,
            "scan": ScanRunner,
            "fix": FixRunner,
            "continuous": ContinuousRunner,
            "command": CommandRunner,
            "resolve": ResolveRunner,
        }
        # Dependencies are injected; default to standard classes
        self._web_loader_cls = web_loader_cls
        self._memory_cls = memory_cls

    def run(self) -> int:
        divider()
        print(f"  PATCHLY — {self.config.mode.upper()} MODE", flush=True)
        print(f"  Provider: {self.config.provider} | Model: {self.config.model}", flush=True)
        divider()

        llm_log("Building context...")
        context = build_context(self.config)
        llm_log(f"Context built: {len(context.get('files', []))} files loaded")

        # Web and memory loading
        web_loader = self._web_loader_cls(context)
        web_content = web_loader.load()

        memory = load_memory()
        memory_mgr = MemoryManager(memory)
        memory_context = memory_mgr.get_memory_context()

        mode = self.config.mode
        llm_log(f"Starting {mode} analysis...")

        # Select and run the appropriate mode runner
        runner_cls = self._runner_map.get(mode)
        if runner_cls is None:
            llm_log(f"Unknown mode: {mode}")
            return 1

        runner = runner_cls(self.config, context, web_content, memory_context)
        results = runner.run()

        # Post‑processing: report and memory
        ReportWriter.write(results, self.config, memory_mgr)
        ReportWriter.record_serious(results, memory_mgr)

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