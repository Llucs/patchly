from __future__ import annotations

from pathlib import Path
from typing import Any

from patchly.config import GITHUB_SHA, WORKSPACE, PatchlyConfig, load_event
from patchly.github_client import get_repo_files


IGNORED_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".tox", ".eggs", "dist", "build", ".next", ".nuxt",
    "vendor", ".bundle", ".terraform", ".serverless",
    "site-packages", "target", "bin", "obj",
}

TEXT_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala",
    ".css", ".scss", ".less", ".html", ".xml", ".svg",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".rst", ".txt",
    ".sql", ".graphql", ".proto", ".gradle",
    "Dockerfile", "Makefile",
}


def build_context(config: PatchlyConfig) -> dict[str, Any]:
    event = load_event()
    ref = GITHUB_SHA or event.get("pull_request", {}).get("head", {}).get("sha", "")

    if config.mode == "review" and ref:
        try:
            remote = get_repo_files(ref)
        except Exception:
            remote = []
    else:
        remote = []

    relevant = []
    for f in remote:
        path = f.get("path", "")
        parts = Path(path).parts
        if any(p in IGNORED_DIRS for p in parts):
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
        "ref": ref or "main",
    }


def list_project_files(root: Path | None = None) -> list[Path]:
    base = root or WORKSPACE
    files = []
    for p in base.rglob("*"):
        if p.is_file():
            rel = p.relative_to(base)
            if not any(part in IGNORED_DIRS for part in rel.parts):
                files.append(p)
    return files