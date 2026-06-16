from __future__ import annotations

from typing import Any


class ActionResult:
    def __init__(
        self,
        analyzer: str,
        severity: str,
        description: str,
        detail: str = "",
        title: str = "",
        files: list[str] | None = None,
    ):
        self.analyzer = analyzer
        self.severity = severity
        lines = description.split("\n")
        self.title = title or (lines[0][:120] if lines else description[:120])
        self.description = description
        self.detail = detail or description
        self.files = files or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzer": self.analyzer,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "detail": self.detail,
            "files": self.files,
        }
