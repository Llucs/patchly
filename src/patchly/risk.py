from __future__ import annotations

from pathlib import Path
from typing import Any

from patchly.actions import ActionResult


RISK_RULES: list[dict[str, Any]] = [
    {"pattern": "auth", "label": "auth/security logic", "score": 1},
    {"pattern": "security", "label": "security logic", "score": 1},
    {"pattern": "ci", "label": "CI/CD configuration", "score": 1},
    {"pattern": "deploy", "label": "deployment logic", "score": 1},
    {"pattern": "secret", "label": "secrets handling", "score": 2},
    {"pattern": "token", "label": "token handling", "score": 2},
    {"pattern": "password", "label": "password handling", "score": 2},
    {"pattern": "database", "label": "database logic", "score": 1},
    {"pattern": "migration", "label": "database migration", "score": 2},
    {"pattern": "config", "label": "configuration", "score": 1},
    {"pattern": "docker", "label": "Docker configuration", "score": 1},
    {"pattern": "Makefile", "label": "build system", "score": 1},
]

MAX_FILES_LOW = 3
MAX_LINES_LOW = 50
MAX_FILES_MEDIUM = 10
MAX_LINES_MEDIUM = 200


def score_issue(issue: ActionResult) -> int:
    score = 0
    desc = (issue.title + " " + issue.description).lower()
    file_count = len(issue.files)

    for rule in RISK_RULES:
        if rule["pattern"] in desc:
            score += rule["score"]

    if file_count > MAX_FILES_MEDIUM:
        score += 2
    elif file_count > MAX_FILES_LOW:
        score += 1

    if any(Path(f).suffix in (".yml", ".yaml") and "deploy" in desc for f in issue.files):
        score += 1

    return score


def classify(score: int) -> str:
    if score <= 1:
        return "low"
    if score <= 3:
        return "medium"
    return "high"


def action_for_score(score: int, config: Any = None) -> str:
    level = classify(score)
    if level == "low":
        return "comment"
    if level == "medium":
        return "pr"
    return "review_required"


def risk_context(files: list[str], description: str) -> str:
    score = 0
    desc = description.lower()
    for rule in RISK_RULES:
        if rule["pattern"] in desc:
            score += rule["score"]
    if len(files) > MAX_FILES_LOW:
        score += 1
    if len(files) > MAX_FILES_MEDIUM:
        score += 1
    level = classify(score)
    action = action_for_score(score)

    return (
        f"Risk assessment: score={score}, level={level}, recommended action={action}."
        if score > 0 else "Risk assessment: score=0, no risk factors detected."
    )
