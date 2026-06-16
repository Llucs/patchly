# IMPORTANT: When making ANY changes to Patchly, you MUST update the version below.
# Read VERSION from parent VERSION file or update this constant directly.
# Follow semver: MAJOR.MINOR.PATCH
#   MAJOR: breaking API/behavior changes
#   MINOR: new features, non-breaking enhancements
#   PATCH: bug fixes, performance improvements

from pathlib import Path

_VERSION_FILE = Path(__file__).resolve().parent.parent.parent / "VERSION"


def _read_version() -> str:
    try:
        return _VERSION_FILE.read_text().strip()
    except (OSError, IOError):
        return "1.3.0"


VERSION = _read_version()

__all__ = ["VERSION"]
