from __future__ import annotations

from patchly.actions import ActionResult
from patchly.github_client import create_issue
from patchly.config import PatchlyConfig


def report_results(results: list[ActionResult], config: PatchlyConfig) -> list[str]:
    urls = []
    if not config.auto_create_issues:
        return urls

    for r in results:
        if r.severity in ("error", "warning"):
            title = f"Patchly: {r.title[:100]}"
            body = (
                f"**Analyzer**: {r.analyzer}\n"
                f"**Severity**: {r.severity}\n\n"
                f"{r.description}\n"
            )
            try:
                issue = create_issue(title, body, ["patchly", r.severity])
                urls.append(issue.get("html_url", ""))
            except Exception:
                pass

    return urls
