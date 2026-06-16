from patchly.utils.validation import validate_python_syntax, is_safe_modification


def test_valid_python():
    errors = validate_python_syntax("x = 1\ny = x + 2\nprint(y)")
    assert errors == []


def test_invalid_python():
    errors = validate_python_syntax("x = ")
    assert len(errors) > 0


def test_safe_path():
    assert is_safe_modification("fix-branch", "src/main.py") is True


def test_unsafe_path():
    assert is_safe_modification("fix-branch", ".env") is False
    assert is_safe_modification("fix-branch", ".git/config") is False
