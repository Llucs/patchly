from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionResult:
    analyzer: str
    severity: str
    description: str
    detail: str = ""
    title: str = ""
    files: list[str] = field(default_factory=list)

    def __init__(self, analyzer: str, severity: str, description: str):
        self.analyzer = analyzer
        self.severity = severity
        lines = description.split("\n")
        self.title = lines[0][:120] if lines else description[:120]
        self.description = description
        self.detail = description
        self.files = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "analyzer": self.analyzer,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "files": self.files,
        }


def execute_actions(results: list[ActionResult]) -> None:
    for r in results:
        pass
