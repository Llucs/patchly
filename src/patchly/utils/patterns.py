from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional, Dict, Tuple


DEPRECATED_PATTERNS: dict[str, list[tuple[str, str, str]]] = {
    ".py": [
        (r"import (\w+)\s+as", "Use `from x import y` style", "import style"),
        (r"print\s*`", "Use print() function", "python2 style"),
        (r"\.format\(", "Use f-strings", "string formatting"),
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


IGNORE_DIRS: List[str] = [
    ".git", "__pycache__", "node_modules", ".venv", "env",
    "dist", "build", ".tox", ".eggs", "*.egg-info", ".mypy_cache",
    ".pytest_cache", ".vscode", ".idea"
]


def scan_directory(
    root: str,
    ignore_dirs: Optional[List[str]] = None,
    extensions: Optional[List[str]] = None,
) -> List[str]:
    """
    Walk through directory using os.scandir, skipping ignored directories.
    Returns a list of file paths matching the given extensions.
    If extensions is None, all files are included.
    """
    if ignore_dirs is None:
        ignore_dirs = IGNORE_DIRS
    results: List[str] = []
    stack: List[str] = []
    try:
        stack.append(os.path.abspath(root))
    except Exception:
        return results

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in ignore_dirs and not entry.name.startswith('.'):
                            stack.append(entry.path)
                    elif entry.is_file():
                        if extensions is None or any(entry.name.endswith(ext) for ext in extensions):
                            results.append(entry.path)
        except PermissionError:
            continue
    return results


def find_patterns_in_directory(
    root: str,
    ignore_dirs: Optional[List[str]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """
    Scan a directory and collect deprecated patterns and secrets from all files.
    Returns a dict with keys 'deprecated' and 'secrets'.
    Each finding dict includes the original fields plus a 'file' key.
    """
    dep_extensions = list(DEPRECATED_PATTERNS.keys())
    all_findings: Dict[str, List[Dict[str, str]]] = {
        'deprecated': [],
        'secrets': [],
    }

    for filepath in scan_directory(root, ignore_dirs, extensions=dep_extensions):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except (IOError, UnicodeDecodeError):
            continue

        ext = Path(filepath).suffix
        dep_findings = find_deprecated_patterns(content, ext)
        for finding in dep_findings:
            finding['file'] = filepath
            all_findings['deprecated'].append(finding)

        sec_findings = find_secrets(content)
        for finding in sec_findings:
            finding['file'] = filepath
            all_findings['secrets'].append(finding)

    return all_findings