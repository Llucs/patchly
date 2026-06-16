from __future__ import annotations

import re


DEPRECATED_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    ".py": [
        (r"import (\w+)\s+as", "Use `from x import y` style", "import style"),
        (r"print\s*`", "Use print() function", "python2 style"),
        (r"(\w+)\.format\(\)", "Use f-strings", "string formatting"),
        (r"os\.path\.(join|exists|isfile)", "Use pathlib.Path", "path handling"),
    ],
    ".js": [
        (r"var\s+(\w+)", "Use const/let instead of var", "ES6 migration"),
        (r"(\.then\(|\.catch\()", "Use async/await", "async patterns"),
    ],
}


def find_deprecated_patterns(
    content: str,
    extension: str,
) -> list[dict[str, str]]:
    findings = []
    patterns = DEPRECATED_PATTERNS.get(extension, [])

    for regex, suggestion, category in patterns:
        for match in re.finditer(regex, content, re.MULTILINE):
            line_num = content[:match.start()].count("\n") + 1
            findings.append({
                "line": str(line_num),
                "pattern": match.group(0),
                "suggestion": suggestion,
                "category": category,
            })

    return findings


def find_secrets(content: str) -> list[dict[str, str]]:
    findings = []
    secret_patterns = [
        (r'(?i)(api[_-]?key|secret|token|password|credential)\s*[=:]\s*["\'][^"\']+["\']', "Possible credential"),
        (r'ghp_[A-Za-z0-9]{36}', "GitHub token"),
        (r'(?i)sk-[A-Za-z0-9]{32,}', "OpenAI key pattern"),
        (r'AKIA[0-9A-Z]{16}', "AWS access key"),
    ]

    for pattern, label in secret_patterns:
        for match in re.finditer(pattern, content):
            line_num = content[:match.start()].count("\n") + 1
            findings.append({
                "line": str(line_num),
                "pattern": match.group(0)[:20] + "...",
                "label": label,
            })

    return findings
