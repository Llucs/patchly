from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from patchly.actions import ActionResult
from patchly.config import PatchlyConfig
from patchly.llm import chat


SEVERITY_TAGS = re.compile(
    r"(?:^|\n)#+\s*(?:Severity|level|risk):\s*(critical|high|medium|low)",
    re.IGNORECASE,
)

ISSUE_PATTERNS = re.compile(
    r"(?:^|\n)(?:- |\* |\d+[.)]\s*)?(?:\*\*)?(?:Issue|Finding|Problem|Bug|Vulnerability)\s*(?:\*\*)?(?:\s*\d*)?[:\s]",
    re.IGNORECASE,
)

ACTIONABLE_KEYWORDS = re.compile(
    r"(bug|vulnerability|security|error|crash|memory\s*leak|injection|XSS|SQLi|broken|incorrect|missing|wrong|fails|not\s*working|deprecated)",
    re.IGNORECASE,
)


class BaseAnalyzer(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def analyze(self, file_contents: str, file_path: Path) -> list[ActionResult]:
        pass

    def _llm_analysis(self, system: str, files_content: str) -> str:
        return chat(
            [{"role": "user", "content": f"{system}\n\nFiles to analyze:\n{files_content[:25000]}"}],
            self.config,
            system=system,
        )

    FILEPATH_RE = re.compile(
        r"(?:\*\*File\*\*|File|Path|Location)\s*:\s*`?([^\n`]+?)`?"
        r"|###\s+`?([^\n`]+?)`?\s*(?:\n|$)",
        re.IGNORECASE,
    )

    def _parse_findings(self, text: str, analyzer_name: str) -> list[ActionResult]:
        text = text.strip()
        if not text:
            return []

        severity = self._detect_severity(text)

        findings = self._split_findings(text)
        if not findings:
            return [ActionResult(analyzer_name, severity, text)]

        results = []
        for f in findings:
            sev = self._detect_severity(f) or severity
            files = self._extract_files(f)
            results.append(ActionResult(analyzer_name, sev, f.strip(), files=files))
        return results

    def _extract_files(self, text: str) -> list[str]:
        matches = self.FILEPATH_RE.findall(text)
        paths = []
        for m in matches:
            path = (m[0] or m[1]).strip().rstrip("`").strip()
            if path and not path.startswith("#") and "/" in path:
                paths.append(path)
        return paths

    def _detect_severity(self, text: str) -> str:
        text_lower = text.lower()
        if re.search(r"(critical|catastrophic|severe)", text_lower):
            return "error"
        if re.search(r"(high|major|important)", text_lower):
            return "error"
        if re.search(r"(medium|moderate|warning)", text_lower):
            return "warning"
        if re.search(r"(low|minor|cosmetic|info|suggestion)", text_lower):
            return "info"
        if ACTIONABLE_KEYWORDS.search(text_lower):
            return "warning"
        return "info"

    def _split_findings(self, text: str) -> list[str]:
        parts = []
        current: list[str] = []
        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if re.match(r"^(?:- |\* |\d+[.)]\s*)?(?:\*\*)?(?:##?\s+\d+\.?\s*|Issue|Finding|Problem|Bug|Vulnerability|Security|Performance|Quality|Architecture)", stripped, re.IGNORECASE):
                if current:
                    parts.append("\n".join(current))
                current = [stripped]
            else:
                current.append(stripped)
        if current:
            parts.append("\n".join(current))
        return parts if len(parts) > 1 else []