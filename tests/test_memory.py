from unittest.mock import patch, MagicMock

from patchly.memory import RepoMemory, load_memory, add_decision, add_pattern, add_known_issue, add_module_rule, save_memory


def test_memory_empty():
    memory = RepoMemory()
    assert memory.to_context() == ""


def test_memory_with_decisions():
    memory = RepoMemory(decisions=[{"decision": "Use pathlib", "reason": "Modern standard", "file": "src/utils.py"}])
    ctx = memory.to_context()
    assert "Past decisions" in ctx
    assert "Use pathlib" in ctx


def test_memory_with_patterns():
    memory = RepoMemory(patterns=[{"pattern": "snake_case", "description": "Use snake_case for functions"}])
    ctx = memory.to_context()
    assert "Known patterns" in ctx
    assert "snake_case" in ctx


def test_memory_with_known_issues():
    memory = RepoMemory(known_issues=[{"issue": "N+1 query in users", "file": "src/users.py", "severity": "warning"}])
    ctx = memory.to_context()
    assert "Known issues" in ctx


def test_memory_with_module_rules():
    memory = RepoMemory(module_rules=[{"module": "auth", "rule": "Do not modify automatically"}])
    ctx = memory.to_context()
    assert "Module rules" in ctx
    assert "auth" in ctx


def test_memory_combined():
    memory = RepoMemory(
        decisions=[{"decision": "Use f-strings", "reason": "Consistency", "file": ""}],
        patterns=[{"pattern": "type hints", "description": "Use type hints everywhere", "module": ""}],
    )
    ctx = memory.to_context()
    assert "Past decisions" in ctx
    assert "Known patterns" in ctx


@patch("patchly.memory.save_memory")
def test_add_decision(save_mock):
    add_decision("Test decision", "Test reason", "test.py")
    assert save_mock.called


@patch("patchly.memory.save_memory")
def test_add_pattern(save_mock):
    add_pattern("snake_case", "Use snake_case for all functions")
    assert save_mock.called


@patch("patchly.memory.save_memory")
def test_add_known_issue(save_mock):
    add_known_issue("Bug in login", "auth/login.py", "error")
    assert save_mock.called


@patch("patchly.memory.save_memory")
@patch("patchly.memory.load_memory")
def test_add_duplicate_module_rule(load_mock, save_mock):
    load_mock.return_value = RepoMemory(
        module_rules=[{"module": "auth", "rule": "Do not modify"}]
    )
    add_module_rule("auth", "Do not modify")
    assert not save_mock.called

    add_module_rule("db", "Use ORM")
    assert save_mock.called
