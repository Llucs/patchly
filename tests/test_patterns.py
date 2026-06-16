from patchly.utils.patterns import find_secrets, find_deprecated_patterns


def test_find_secrets_none():
    content = "x = 5\ny = 10"
    assert find_secrets(content) == []


def test_find_secrets_github_token():
    content = "token = ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    results = find_secrets(content)
    assert len(results) > 0
    assert results[0]["label"] == "GitHub token"


def test_find_secrets_api_key():
    content = 'API_KEY = "sk-mysecretkey12345678901234567890"'
    results = find_secrets(content)
    assert len(results) > 0


def test_find_deprecated_python():
    content = 'print("hello")\nresult = "{}".format(x)'
    results = find_deprecated_patterns(content, ".py")
    assert len(results) > 0
    assert results[0]["category"] == "string formatting"
