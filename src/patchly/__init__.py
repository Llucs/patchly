from importlib.metadata import PackageNotFoundError, version as _pkg_version
from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "VERSION"


def _read_version() -> str:
    try:
        return _VERSION_FILE.read_text().strip()
    except (OSError, IOError):
        pass
    try:
        return _pkg_version("patchly")
    except PackageNotFoundError:
        return "0.0.0"


VERSION = _read_version()

__all__ = ["VERSION"]