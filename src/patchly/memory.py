from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from patchly.config import PATCHLY_DIR, WORKSPACE


MEMORY_DIR = WORKSPACE / PATCHLY_DIR / "memory"
DECISIONS_FILE = MEMORY_DIR / "decisions.json"
PATTERNS_FILE = MEMORY_DIR / "patterns.json"
KNOWN_ISSUES_FILE = MEMORY_DIR / "known-issues.json"
MODULE_RULES_FILE = MEMORY_DIR / "module-rules.json"


@dataclass
class RepoMemory:
    decisions: list[dict[str, Any]] = field(default_factory=list)
    patterns: list[dict[str, Any]] = field(default_factory=list)
    known_issues: list[dict[str, Any]] = field(default_factory=list)
    module_rules: list[dict[str, Any]] = field(default_factory=list)

    def to_context(self) -> str:
        parts = []
        if self.decisions:
            parts.append("## Past decisions\n" + "\n".join(
                f"- {d['decision']} ({d['reason']})" for d in self.decisions[-5:]
            ))
        if self.patterns:
            parts.append("## Known patterns\n" + "\n".join(
                f"- {p['pattern']}: {p['description']}" for p in self.patterns[-5:]
            ))
        if self.known_issues:
            parts.append("## Known issues\n" + "\n".join(
                f"- {i['issue']} in {i.get('file', '?')}" for i in self.known_issues[-5:]
            ))
        if self.module_rules:
            parts.append("## Module rules\n" + "\n".join(
                f"- {r['module']}: {r['rule']}" for r in self.module_rules[-5:]
            ))
        return "\n\n".join(parts) if parts else ""


def _ensure_dir() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> list[dict[str, Any]]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _write_json(path: Path, data: list[dict[str, Any]]) -> None:
    _ensure_dir()
    path.write_text(json.dumps(data, indent=2))


def load_memory() -> RepoMemory:
    return RepoMemory(
        decisions=_read_json(DECISIONS_FILE),
        patterns=_read_json(PATTERNS_FILE),
        known_issues=_read_json(KNOWN_ISSUES_FILE),
        module_rules=_read_json(MODULE_RULES_FILE),
    )


def save_memory(memory: RepoMemory) -> None:
    _write_json(DECISIONS_FILE, memory.decisions)
    _write_json(PATTERNS_FILE, memory.patterns)
    _write_json(KNOWN_ISSUES_FILE, memory.known_issues)
    _write_json(MODULE_RULES_FILE, memory.module_rules)


def add_decision(decision: str, reason: str, file: str = "") -> None:
    memory = load_memory()
    memory.decisions.append({"decision": decision, "reason": reason, "file": file, "timestamp": datetime.now(timezone.utc).isoformat()})
    if len(memory.decisions) > 100:
        memory.decisions = memory.decisions[-100:]
    save_memory(memory)


def add_pattern(pattern: str, description: str, module: str = "") -> None:
    memory = load_memory()
    memory.patterns.append({"pattern": pattern, "description": description, "module": module})
    if len(memory.patterns) > 50:
        memory.patterns = memory.patterns[-50:]
    save_memory(memory)


def add_known_issue(issue: str, file: str, severity: str = "info") -> None:
    memory = load_memory()
    memory.known_issues.append({"issue": issue, "file": file, "severity": severity, "timestamp": datetime.now(timezone.utc).isoformat()})
    if len(memory.known_issues) > 100:
        memory.known_issues = memory.known_issues[-100:]
    save_memory(memory)


def add_module_rule(module: str, rule: str) -> None:
    memory = load_memory()
    exists = any(r["module"] == module and r["rule"] == rule for r in memory.module_rules)
    if not exists:
        memory.module_rules.append({"module": module, "rule": rule})
        save_memory(memory)
