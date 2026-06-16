from pathlib import Path
from patchly.actions import ActionResult
from patchly.config import PatchlyConfig


def test_action_result_creation():
    r = ActionResult("test", "info", "This is a test result title\nMore details here")
    assert r.analyzer == "test"
    assert r.severity == "info"
    assert "test result title" in r.title


def test_action_result_to_dict():
    r = ActionResult("security", "error", "Found vulnerability in auth.py")
    d = r.to_dict()
    assert d["analyzer"] == "security"
    assert d["severity"] == "error"
    assert "vulnerability" in d["title"]


def test_config_defaults():
    cfg = PatchlyConfig()
    assert cfg.mode == "review"
    assert cfg.auto_mode == "suggest"
    assert "code_quality" in cfg.analyzers
    assert cfg.analyzers["code_quality"].enabled is True
