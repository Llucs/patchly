from __future__ import annotations

import ast
import re
from pathlib import Path


def is_safe_modification(branch: str, file_path: str) -> bool:
    forbidden = {".git", ".env", "node_modules"}
    parts = Path(file_path).parts
    return not any(p in forbidden for p in parts)


def validate_python_syntax(content: str) -> list[str]:
    errors = []
    try:
        ast.parse(content)
    except SyntaxError as e:
        errors.append(f"Python syntax error: {e}")
    return errors


def validate_syntax(content: str, extension: str) -> list[str]:
    if extension == ".py":
        return validate_python_syntax(content)
    return []
