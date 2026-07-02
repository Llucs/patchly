from __future__ import annotations

from pathlib import Path

from patchly.actions import ActionResult
from patchly.analyzers.base import BaseAnalyzer


SYSTEM = """You are a code modernization analyzer. Analyze the provided source code and identify:

1. Deprecated API usage across languages and frameworks
2. Outdated language features (e.g., old Python/JS patterns)
3. Legacy libraries or frameworks that should be upgraded
4. Manual patterns now handled by language/stdlib features
5. Very old dependency versions
6. Non-idiomatic patterns for the language version in use

For each issue, provide: file path, the outdated pattern, the recommended modern alternative, and estimated effort to update.

Output format:
## Modernization Opportunity
- **File**: <path>
- **Outdated pattern**: <current code>
- **Modern alternative**: <new code>
- **Effort**: low/medium/high
"""


class ModernizationAnalyzer(BaseAnalyzer):
    def analyze(self, files: list[Path], file_contents: dict[str, str] | None = None) -> list[ActionResult]:
        content_batches = []
        for f in files:
            if file_contents is not None and str(f) in file_contents:
                text = file_contents[str(f)]
            else:
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
            if text.strip():
                content_batches.append(f"### {f}\n```\n{text[:2000]}\n```")

        if not content_batches:
            return []

        result = self._llm_analysis(SYSTEM, "\n\n".join(content_batches))
        return self._parse_findings(result, "modernization")