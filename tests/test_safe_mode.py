import pytest

from patchly.config import SafeModeConfig
from patchly.safe_mode import check_safe, SafeModeError


def test_safe_mode_disabled():
    config = SafeModeConfig(enabled=False)
    assert check_safe(["any/file.py"], "anything", config) is None


def test_safe_mode_allows_normal():
    config = SafeModeConfig(enabled=True)
    assert check_safe(["src/app.py"], "fix lint error", config) is None


def test_safe_mode_blocks_critical():
    config = SafeModeConfig(enabled=True, block_destructive_changes=True)
    with pytest.raises(SafeModeError):
        check_safe([".github/workflows/deploy.yml"], "update ci config", config)


def test_safe_mode_warns_critical():
    config = SafeModeConfig(enabled=True, block_destructive_changes=False)
    result = check_safe([".env"], "update config", config)
    assert result is not None
    assert "Blocked" in result or "critical" in result.lower()


def test_safe_mode_blocks_too_many_files():
    config = SafeModeConfig(enabled=True, max_file_changes=2, block_destructive_changes=True)
    files = [f"file{i}.py" for i in range(5)]
    with pytest.raises(SafeModeError):
        check_safe(files, "bulk change", config)


def test_safe_mode_warns_review():
    config = SafeModeConfig(enabled=True, require_diff_validation=True)
    result = check_safe(["src/api.py"], "change public interface", config)
    assert result is not None
    assert "Requires review" in result
