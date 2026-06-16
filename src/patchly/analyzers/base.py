from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from patchly.actions import ActionResult
from patchly.config import PatchlyConfig
from patchly.llm import chat


class BaseAnalyzer(ABC):
    def __init__(self, config: PatchlyConfig):
        self.config = config

    @abstractmethod
    def analyze(self, files: list[Path]) -> list[ActionResult]:
        pass

    def _llm_analysis(self, system: str, files_content: str) -> str:
        return chat(
            [{"role": "user", "content": f"{system}\n\nFiles to analyze:\n{files_content[:25000]}"}],
            self.config,
            system=system,
        )
