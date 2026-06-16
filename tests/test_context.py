from pathlib import Path
from patchly.context import IGNORED_PATTERNS, TEXT_EXTENSIONS


def test_ignored_patterns():
    assert ".git" in IGNORED_PATTERNS
    assert "node_modules" in IGNORED_PATTERNS


def test_text_extensions():
    assert ".py" in TEXT_EXTENSIONS
    assert ".js" in TEXT_EXTENSIONS
    assert ".md" in TEXT_EXTENSIONS


def test_ignored_path_detection():
    parts = ("project", ".git", "config")
    assert any(p in IGNORED_PATTERNS for p in parts)

    parts = ("project", "src", "main.py")
    assert not any(p in IGNORED_PATTERNS for p in parts)
