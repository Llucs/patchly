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
        file_contents: dict[Path | str, str] | None = None,
        file_path: Path | None = None,
    ) -> list[ActionResult]:
        structure = []
        file_contents_to_analyze = []

        for f in files:
            relative = f.relative_to(Path.cwd())
            structure.append(str(relative))

            content = None
            if file_contents is not None:
                for key in (f, str(f), relative, str(relative)):
                    content = file_contents.get(key)
                    if content is not None:
                        break

            if content is None and f.is_file():
                content = f.read_text(errors="replace")

            if content is not None:
                file_contents_to_analyze.append(f"--- {relative} ---\n{content}")

        if not structure:
            return []

        user_content = (
            f"Repository structure ({len(structure)} files):\n"
            + "\n".join(structure)
        )
        if file_contents_to_analyze:
            user_content += (
                "\n\nFile contents:\n" + "\n\n".join(file_contents_to_analyze)
            )

        result = self._llm_analysis(SYSTEM, user_content)
        return self._parse_findings(result, "architecture")