from __future__ import annotations

from pathlib import Path
from typing import Any

from patchly.config import WORKSPACE, PatchlyConfig, load_event
from patchly.github_client import get_repo_files


IGNORED_PATTERNS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", ".eggs", "dist", "build", ".next", ".nuxt",
    "vendor", ".bundle", ".terraform", ".serverless",
    "site-packages", "target", "bin", "obj",
}

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala", ".ex", ".exs", ".clj", ".cljs",
    ".css", ".scss", ".less", ".html", ".htm", ".xml", ".svg",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".rst", ".txt", ".env", ".gitignore", ".dockerfile",
    ".sql", ".graphql", ".proto", ".gradle", ".makefile",
    "Dockerfile", "Makefile", "docker-compose.yml",
}


def build_context(config: PatchlyConfig) -> dict[str, Any]:
    event = load_event()
    ref = event.get("pull_request", {}).get("head", {}).get("sha", "") or config.model

    files = get_repo_files(ref)
    relevant = []
    for f in files:
        path = f.get("path", "")
        parts = Path(path).parts
        if any(p in IGNORED_PATTERNS for p in parts):
            continue
        ext = Path(path).suffix
        if ext.lower() in TEXT_EXTENSIONS or Path(path).name in TEXT_EXTENSIONS:
            relevant.append(f)
        if len(relevant) >= config.max_files_per_run:
            break

    return {
        "repository": event.get("repository", {}).get("full_name", ""),
        "files": relevant,
        "event": event,
        "ref": ref,
    }


def list_project_files() -> list[Path]:
    result = []
    for p in WORKSPACE.rglob("*"):
        if p.is_file():
            parts = p.relative_to(WORKSPACE).parts
            if not any(part in IGNORED_PATTERNS for part in parts):
                result.append(p)
    return sorted(result)
