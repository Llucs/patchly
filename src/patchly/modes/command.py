from __future__ import annotations

from patchly.config import PatchlyConfig, load_event
from patchly.llm import chat
from patchly.github_client import create_comment


ISSUE_COMMAND_SYSTEM = """You are Patchly executing a developer's command inside an issue or comment.

Extract the command from the comment body. Commands start with /patchly followed by the instruction.

Execute the request and provide a clear response. If the request is unclear, explain what you can do.
"""


def execute(config: PatchlyConfig) -> str | None:
    event = load_event()
    comment_body = (event.get("comment") or {}).get("body", "")
    issue_number = (event.get("issue") or {}).get("number")

    if not comment_body or not issue_number:
        return None

    response = chat(
        [{"role": "user", "content": f"Comment: {comment_body}\n\nRespond to this command."}],
        config,
        system=ISSUE_COMMAND_SYSTEM,
    )

    create_comment(issue_number, response)
    return response
