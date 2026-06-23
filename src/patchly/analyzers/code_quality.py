from __future__ import annotations
from typing import Optional

from pathlib import Path

from patchly.actions import ActionResult
from patchly.analyzers.base import BaseAnalyzer


SYSTEM = """You are a code quality analyzer. Analyze the provided source files and identify:

1. Overly complex functions/methods (high cyclomatic complexity)
2. Duplicated code blocks
3. Poor naming conventions
4. Missing error handling
5. Excessive nesting depth
6. Dead code or commented-out code
7. Inconsistent style or formatting issues

For each issue, provide: file path, line numbers, the problem, and a concrete fix suggestion.

Output format:
## File: <path>
- **Line N**: <issue description> → <fix suggestion>
"""


class CodeQualityAnalyzer(BaseAnalyzer):
    def analyze(self, files: list[Path], file_contents: Optional[dict] = None) -> list[ActionResult]:
        content_batches = []
        for f in files:
            try:
                if file_contents is not None and str(f) in file_contents:
                    text = file_contents[str(f)]
                else:
                    text = f.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    content_batches.append(f"### {f}\n```\n{text[:3000]}\n```")
            except Exception:
                pass

        if not content_batches:
            return []

        result = self._llm_analysis(SYSTEM, "\n\n".join(content_batches))
        return self._parse_findings(result, "code_quality")