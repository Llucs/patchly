from __future__ import annotations

from pathlib import Path
from typing import Any

from patchly.config import SafeModeConfig

CRITICAL_PATTERNS = [
    "config", "secret", "credential", "password", "token", "auth",
    ".github/workflows", "Dockerfile", "docker-compose",
    ".env", ".gitignore", "package.json", "requirements.txt",
    "Makefile", "ci", "cd", "deploy",
]

REQUIRE_REVIEW_PATTERNS = [
    "api", "interface", "protocol", "contract",
    "migration", "schema", "database",
    "middleware", "handler", "controller",
    "public", "export", "__init__",
    "setup.py", "setup.cfg", "pyproject.toml",
]


class SafeModeError(Exception):
    pass


def check_safe(
    files: list[str],
    description: str,
    config: SafeModeConfig,
) -> str | None:
    if not config.enabled:
        return None

    desc_lower = description.lower()
    critical_found = []
    review_found = []

    for f in files:
        path = Path(f)
        for pattern in CRITICAL_PATTERNS:
            if pattern in str(path) or pattern in desc_lower:
                critical_found.append((f, pattern))
                break

    for f in files:
        path = Path(f)
        for pattern in REQUIRE_REVIEW_PATTERNS:
            if pattern in str(path) or pattern in desc_lower:
                review_found.append((f, pattern))
                break

    if critical_found:
        files_list = ", ".join(f for f, _ in critical_found)
        msg = f"Blocked by safe_mode: {files_list} matched critical patterns"
        if config.block_destructive_changes:
            raise SafeModeError(msg)
        return msg

    if len(files) > config.max_file_changes:
        msg = f"Change touches {len(files)} files (limit: {config.max_file_changes})"
        if config.block_destructive_changes:
            raise SafeModeError(msg)
        return msg

    if config.require_diff_validation:
        if review_found:
            files_list = ", ".join(f for f, _ in review_found)
            return f"Requires review: {files_list} matched review-required patterns"

    return None
