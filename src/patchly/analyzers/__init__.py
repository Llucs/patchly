from __future__ import annotations

from pathlib import Path

from patchly.actions import ActionResult
from patchly.config import PatchlyConfig


def run_analyzers(files: list[Path], config: PatchlyConfig) -> list[ActionResult]:
    from patchly.analyzers.code_quality import CodeQualityAnalyzer
    from patchly.analyzers.architecture import ArchitectureAnalyzer
    from patchly.analyzers.performance import PerformanceAnalyzer
    from patchly.analyzers.modernization import ModernizationAnalyzer
    from patchly.analyzers.security import SecurityAnalyzer

    analyzer_map = {
        "code_quality": CodeQualityAnalyzer,
        "architecture": ArchitectureAnalyzer,
        "performance": PerformanceAnalyzer,
        "modernization": ModernizationAnalyzer,
        "security": SecurityAnalyzer,
    }

    # Pre-load file contents once to avoid redundant I/O across analyzers
    file_contents: dict[Path, str] = {}
    for file in files:
        try:
            file_contents[file] = file.read_text()
        except Exception:
            # Skip files that cannot be read
            continue

    results = []
    for name, acfg in config.analyzers.items():
        if not acfg.enabled:
            continue
        cls = analyzer_map.get(name)
        if cls is None:
            continue
        analyzer = cls(config)
        try:
            batch = analyzer.analyze(file_contents)
            results.extend(batch)
        except Exception as e:
            results.append(ActionResult(name, "error", f"Analyzer failed: {e}"))

    return results