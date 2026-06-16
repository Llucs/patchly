from __future__ import annotations

from patchly.config import PatchlyConfig
from patchly.github_client import create_comment, get_pr_diff, get_pr
from patchly.llm import chat


def review_pr(pr_number: int, config: PatchlyConfig) -> str:
    pr = get_pr(pr_number)
    diff = get_pr_diff(pr_number)

    prompt = (
        f"Review pull request #{pr_number}: {pr.get('title', '')}\n\n"
        f"Description: {pr.get('body', '')}\n\n"
        f"--- DIFF ---\n{diff[:30000]}\n\n"
        "Analyze for: bugs, code quality issues, security vulnerabilities, "
        "architectural impact, performance problems, and missing test coverage. "
        "Provide actionable feedback per file."
    )

    result = chat([{"role": "user", "content": prompt}], config)

    if config.comment_on_pr:
        create_comment(pr_number, result)

    return result
