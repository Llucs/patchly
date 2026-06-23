from __future__ import annotations

from pathlib import Path

from patchly.actions import ActionResult
from patchly.analyzers.base import BaseAnalyzer


SYSTEM = """You are a performance analyzer. Analyze the provided source code and identify:

1. N+1 query patterns in database access
2. Unnecessary allocations in hot paths
3. Missing caching opportunities
4. Inefficient algorithms or data structures
5. Blocking I/O in async contexts
6. Large objects held in memory unnecessarily
7. Unoptimized loops or list comprehensions

For each issue, provide: file path, line numbers, performance impact, and specific optimization.

Output format:
## Performance Issue
- **File**: <path>
- **Problem**: <description>
- **Severity**: high/medium/low
- **Fix**: <specific code change>
"""


class PerformanceAnalyzer(BaseAnalyzer):
    def analyze(self, files: list[Path], file_contents: str | None = None, **kwargs) -> list[ActionResult]:
        content_batches = []
        if file_contents is not None:
            # Use provided content directly
            content_batches.append(f"### Provided Code\n```\n{file_contents[:2000]}\n```")
        else:
            for f in files:
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                    if text.strip():
                        content_batches.append(f"### {f}\n```\n{text[:2000]}\n```")
                except Exception:
                    pass

        if not content_batches:
            return []

        result = self._llm_analysis(SYSTEM, "\n\n".join(content_batches))
        return self._parse_findings(result, "performance")