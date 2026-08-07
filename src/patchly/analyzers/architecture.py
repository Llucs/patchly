from __future__ import annotations

from pathlib import Path

from patchly.actions import ActionResult
from patchly.analyzers.base import BaseAnalyzer


SYSTEM = """You are an architecture analyzer. Analyze the repository structure and identify:

1. Excessive coupling between modules
2. Circular dependencies
3. Violations of layering (e.g., UI mixing with data access)
4. God objects or god classes doing too much
5. Missing abstractions or inappropriate abstraction levels
6. Package/module organization problems
7. Tight coupling to specific implementations over interfaces

For each issue, provide: the affected components, the architectural problem, and a concrete refactoring approach.

Output format:
## Architectural Issue
- **Problem**: <description>
- **Location**: <modules/files involved>
- **Impact**: <why it matters>
- **Suggestion**: <concrete fix>
"""


class ArchitectureAnalyzer(BaseAnalyzer):
    def analyze(
        self,
        files: list[Path],
        file_contents: dict[Path, str] | None = None,
    ) -> list[ActionResult]:
        cwd = Path.cwd()
        structure = []
        for f in files:
            rel_path = f.relative_to(cwd)
            content = None
            if file_contents is not None:
                content = file_contents.get(f)
                if content is None:
                    content = file_contents.get(str(f))
                if content is None:
                    content = file_contents.get(str(rel_path))
            if content is None:
                try:
                    content = f.read_text()
                except (OSError, UnicodeDecodeError):
                    content = ""
            structure.append(f"### {rel_path}\n{content}\n")

        if not structure:
            return []

        result = self._llm_analysis(
            SYSTEM,
            f"Repository structure ({len(structure)} files):\n" + "\n".join(structure),
        )
        return self._parse_findings(result, "architecture")