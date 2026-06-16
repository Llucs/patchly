from __future__ import annotations

from patchly.config import PatchlyConfig, load_event
from patchly.actions.pr_review import review_pr


def execute(config: PatchlyConfig) -> str | None:
    event = load_event()
    pr_data = event.get("pull_request") or event.get("issue", {}).get("pull_request")
    if pr_data is None:
        return None

    pr_number = pr_data.get("number") or event.get("issue", {}).get("number")
    if pr_number is None:
        return None

    return review_pr(pr_number, config)
