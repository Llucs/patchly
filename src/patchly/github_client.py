from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import httpx

from patchly.config import GITHUB_REPOSITORY, GITHUB_TOKEN


API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"token {GITHUB_TOKEN}",
    "User-Agent": "patchly",
}

client = httpx.Client(
    base_url=API,
    headers=HEADERS,
    timeout=httpx.Timeout(30.0),
    limits=httpx.Limits(
        max_keepalive_connections=10,
        max_connections=20,
        keepalive_expiry=30.0,
    ),
)


def _github_api(
    method: str,
    path: str,
    data: dict[str, Any] | None = None,
) -> Any:
    resp = client.request(method, path, json=data)
    if resp.status_code == 403:
        raise PermissionError(
            f"GitHub API 403 on {method} {path}. "
            "Check that your GITHUB_TOKEN has the required permissions. "
            "Add `permissions:` to your workflow:\n\n"
            "permissions:\n"
            "  contents: write\n"
            "  pull-requests: write\n"
            "  issues: write\n"
        )
    resp.raise_for_status()
    if resp.text:
        return resp.json()
    return {}


def get_pr(pr_number: int) -> dict[str, Any]:
    return _github_api("GET", f"/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}")


def get_pr_files(pr_number: int) -> list[dict[str, Any]]:
    files = []
    page = 1
    while True:
        batch = _github_api(
            "GET",
            f"/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}/files?per_page=100&page={page}",
        )
        if not batch:
            break
        files.extend(batch)
        page += 1
    return files


def get_pr_diff(pr_number: int) -> str:
    path = f"/repos/{GITHUB_REPOSITORY}/pulls/{pr_number}"
    resp = client.get(path, headers={"Accept": "application/vnd.github.v3.diff"})
    resp.raise_for_status()
    return resp.text


def get_file_content(path: str, ref: str = "main") -> str | None:
    try:
        data = _github_api(
            "GET",
            f"/repos/{GITHUB_REPOSITORY}/contents/{path}?ref={ref}",
        )
        if isinstance(data, dict) and data.get("content"):
            return base64.b64decode(data["content"]).decode()
    except Exception:
        return None


def create_comment(pr_number: int, body: str) -> dict[str, Any]:
    return _github_api(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/issues/{pr_number}/comments",
        {"body": body},
    )


def create_issue(title: str, body: str, labels: list[str] | None = None) -> dict[str, Any]:
    return _github_api(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/issues",
        {"title": title, "body": body, "labels": labels or ["patchly"]},
    )


def list_issues(label: str = "patchly", state: str = "open") -> list[dict[str, Any]]:
    issues = []
    page = 1
    while True:
        batch = _github_api(
            "GET",
            f"/repos/{GITHUB_REPOSITORY}/issues?labels={label}&state={state}&per_page=100&page={page}",
        )
        if not batch:
            break
        issues.extend(batch)
        page += 1
    return issues


def add_labels(issue_number: int, labels: list[str]) -> dict[str, Any]:
    return _github_api(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/issues/{issue_number}/labels",
        {"labels": labels},
    )


def update_issue(issue_number: int, data: dict[str, Any]) -> dict[str, Any]:
    return _github_api(
        "PATCH",
        f"/repos/{GITHUB_REPOSITORY}/issues/{issue_number}",
        data,
    )


def create_pr(title: str, body: str, head: str, base: str = "main") -> dict[str, Any]:
    return _github_api(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/pulls",
        {"title": title, "body": body, "head": head, "base": base},
    )


def create_branch(branch_name: str, sha: str) -> dict[str, Any]:
    return _github_api(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/git/refs",
        {"ref": f"refs/heads/{branch_name}", "sha": sha},
    )


def create_commit(
    branch: str,
    message: str,
    tree: str,
) -> dict[str, Any]:
    return _github_api(
        "POST",
        f"/repos/{GITHUB_REPOSITORY}/git/commits",
        {"message": message, "tree": tree, "parents": [get_branch_sha(branch)]},
    )


DEFAULT_BRANCH: str | None = None


def get_default_branch() -> str:
    global DEFAULT_BRANCH
    if DEFAULT_BRANCH is not None:
        return DEFAULT_BRANCH
    try:
        data = _github_api("GET", f"/repos/{GITHUB_REPOSITORY}")
        DEFAULT_BRANCH = data.get("default_branch", "main")
    except Exception:
        DEFAULT_BRANCH = "main"
    return DEFAULT_BRANCH


def get_branch_sha(branch: str | None = None) -> str:
    branch = branch or get_default_branch()
    data = _github_api("GET", f"/repos/{GITHUB_REPOSITORY}/git/refs/heads/{branch}")
    return data["object"]["sha"]


def get_repo_files(ref: str = "main") -> list[dict[str, Any]]:
    return _walk_tree(ref)


def _walk_tree(ref: str, tree_sha: str | None = None) -> list[dict[str, Any]]:
    if tree_sha is None:
        data = _github_api("GET", f"/repos/{GITHUB_REPOSITORY}/git/trees/{ref}?recursive=1")
        items = data.get("tree", [])
    else:
        data = _github_api("GET", f"/repos/{GITHUB_REPOSITORY}/git/trees/{tree_sha}")
        items = data.get("tree", [])
    return [i for i in items if i["type"] == "blob"]


def get_file_at_ref(path: str, ref: str) -> str | None:
    return get_file_content(path, ref)