from __future__ import annotations

from patchly.github_client import create_comment


def post_pr_comment(pr_number: int, body: str) -> dict | None:
    try:
        return create_comment(pr_number, body)
    except Exception:
        return None
