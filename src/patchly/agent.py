from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from patchly.config import (
    PATCHLY_DIR,
    WORKSPACE,
    PatchlyConfig,
    load_config,
)
from patchly.llm import PATCHLY_SYSTEM_PROMPT, chat
from patchly.analyzers import run_analyzers
from patchly.actions import execute_actions, ActionResult
from patchly.context import build_context, list_project_files


REPORTS_DIR = WORKSPACE / PATCHLY_DIR / "reports"


class Agent:
    def __init__(self, config: PatchlyConfig | None = None):
        self.config = config or load_config()
        self.context: dict[str, Any] = {}

    def run(self) -> int:
        self.context = build_context(self.config)
        mode = self.config.mode

        self._log(f"Mode: {mode}")
        self._log(f"Model: {self.config.model}")

        if mode == "review":
            results = self._run_review()
        elif mode == "scan":
            results = self._run_scan()
        elif mode == "command":
            results = self._run_command()
        else:
            self._log(f"Unknown mode: {mode}")
            return 1

        self._write_report(results)

        has_issues = any(r.severity == "error" for r in results)
        return 1 if has_issues else 0

    def _run_review(self) -> list[ActionResult]:
        event = self.context.get("event", {})
        pr_data = event.get("pull_request", {})
        pr_number = pr_data.get("number")

        self._log(f"Reviewing PR #{pr_number}")

        from patchly.github_client import get_pr_diff, create_comment

        diff = get_pr_diff(pr_number)
        pr_info = {
            "title": pr_data.get("title", ""),
            "body": pr_data.get("body", ""),
            "number": pr_number,
            "diff": diff[:30000] if diff else "",
        }

        analysis_result = chat(
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
        )

        if self.config.comment_on_pr:
            create_comment(pr_number, analysis_result)

        return [ActionResult("review", "info", analysis_result)]

    def _run_scan(self) -> list[ActionResult]:
        self._log("Scanning repository")

        files = list_project_files()
        source_files = [
            f for f in files
            if f.suffix in {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
                ".java", ".rb", ".php", ".c", ".cpp", ".cs",
            }
            and f.stat().st_size > 0
        ]

        if not source_files:
            self._log("No source files found")
            return []

        selected = source_files[:self.config.max_files_per_run * 2]

        results = run_analyzers(selected, self.config)

        if results and self.config.auto_create_issues:
            from patchly.github_client import create_issue

            for r in results:
                if r.severity in ("error", "warning"):
                    create_issue(
                        f"Patchly: {r.title}",
                        f"{r.description}\n\n```\n{r.detail[:5000]}\n```",
                        [f"{self.config.label_prefix}", r.severity],
                    )

        return results

    def _run_command(self) -> list[ActionResult]:
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

        self._log(f"Command: {cmd or 'scan'}")

        if not cmd or cmd in ("scan", "analyze"):
            return self._run_scan()

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

        result = chat([{"role": "user", "content": command_prompt}], self.config)

        return [ActionResult("command", "info", result)]

    def _write_report(self, results: list[ActionResult]) -> None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().isoformat()
        report = {
            "timestamp": timestamp,
            "mode": self.config.mode,
            "results": [r.to_dict() for r in results],
        }
        path = REPORTS_DIR / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}.json"
        path.write_text(json.dumps(report, indent=2))

    def _log(self, msg: str) -> None:
        print(f"[patchly] {msg}", flush=True)
