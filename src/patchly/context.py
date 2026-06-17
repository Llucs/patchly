from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, List, Optional

from patchly.policies.file_filtering import IGNORED_DIRS, TEXT_EXTENSIONS


# Event system
class ContextEvent:
    def __init__(self, context: Optional[dict[str, Any]] = None) -> None:
        self.context = context or {}


class ContextObserver:
    def on_building(self, event: ContextEvent) -> None:
        pass

    def on_built(self, event: ContextEvent) -> None:
        pass


_observers: List[ContextObserver] = []


def register_observer(observer: ContextObserver) -> None:
    _observers.append(observer)


def unregister_observer(observer: ContextObserver) -> None:
    _observers.remove(observer)


def build_context(
    config: Any,
    ref: str,
    remote_file_repo: Callable[[str], list[dict]],
    workspace: Path,
    event_data: dict[str, Any],
) -> dict[str, Any]:
    # Notify observers
    event = ContextEvent()
    for obs in _observers:
        obs.on_building(event)

    mode = getattr(config, 'mode', 'review')

    if mode == "review" and ref:
        try:
            remote = remote_file_repo(ref)
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

    context = {
        "repository": event_data.get("repository", {}).get("full_name", ""),
        "files": relevant,
        "event": event_data,
        "ref": ref or "main",
    }

    event.context = context
    for obs in _observers:
        obs.on_built(event)

    return context


def list_project_files(root: Path | None = None) -> list[Path]:
    base = root or Path.cwd()
    files = []
    for p in base.rglob("*"):
        if p.is_file():
            rel = p.relative_to(base)
            if not any(part in IGNORED_DIRS for part in rel.parts):
                files.append(p)
    return sorted(files)