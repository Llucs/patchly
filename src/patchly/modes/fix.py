from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

import httpx

from patchly.actions import ActionResult
from patchly.config import PATCHLY_DIR, WORKSPACE, PatchlyConfig
from patchly.github_client import (
    API,
    HEADERS,
    GITHUB_REPOSITORY,
    create_pr,
    get_branch_sha,
    get_file_content,
)
from patchly.llm import chat, log as llm_log

FIXES_DIR = WORKSPACE / PATCHLY_DIR / "fixes"


def execute(config: PatchlyConfig) -> list[ActionResult]:
    from patchly.agent import Agent

    agent = Agent(config)
    return agent._run_fix("", load_memory_context())


def load_memory_context() -> str:
    from patchly.memory import load_memory
    return load_memory().to_context()


def _generate_fix(issue: ActionResult, config: PatchlyConfig) -> ActionResult | None:
    if not issue.files:
        return None

    file_path = issue.files[0]
    content = get_file_content(file_path)
    if content is None:
        local_path = WORKSPACE / file_path
        if local_path.exists():
            content = local_path.read_text()
        else:
            llm_log(f"  Cannot fetch {file_path} — file not found")
            return None

    prompt = (
        f"Fix this issue in `{file_path}`:\n\n"
        f"Issue: {issue.title}\n"
        f"Description: {issue.description}\n\n"
        f"Current code:\n"
        f"```\n{content[:8000]}\n```\n\n"
        "Return ONLY the corrected file content as plain text. "
        "No explanations, no markdown fences, no code block markers."
    )

    new_content = chat([{"role": "user", "content": prompt}], config)
    if not new_content or new_content.strip() == content.strip():
        llm_log("  Generated fix matches original — skipping")
        return None

    new_content = _clean_fix_output(new_content)

    fix_detail = json.dumps({
        "file": file_path,
        "original_content": content,
        "new_content": new_content,
    }, indent=2)

    return ActionResult("fix", "info", f"Generated fix for {file_path}", detail=fix_detail)


def _clean_fix_output(text: str) -> str:
    lines = text.strip().split("\n")
    cleaned = []
    for line in lines:
        if line.strip().startswith("```"):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def _apply_fix_as_pr(issue: ActionResult, fix: ActionResult, config: PatchlyConfig) -> str | None:
    try:
        fix_data = json.loads(fix.detail)
    except (json.JSONDecodeError, KeyError):
        llm_log("  Invalid fix data")
        return None

    file_path = fix_data.get("file", "")
    new_content = fix_data.get("new_content", "")
    if not file_path or not new_content:
        return None

    branch_name = f"patchly/fix/{Path(file_path).stem}-{os.urandom(4).hex()}"
    llm_log(f"  Creating branch {branch_name}...")

    try:
        main_sha = get_branch_sha("main")
    except Exception as e:
        llm_log(f"  Cannot get main branch SHA: {e}")
        return None

    ref_resp = httpx.post(
        f"{API}/repos/{GITHUB_REPOSITORY}/git/refs",
        headers=HEADERS,
        json={"ref": f"refs/heads/{branch_name}", "sha": main_sha},
        timeout=15,
    )
    if ref_resp.status_code not in (200, 201):
        llm_log(f"  Branch creation failed: {ref_resp.status_code}")
        return None

    try:
        info = httpx.get(
            f"{API}/repos/{GITHUB_REPOSITORY}/contents/{file_path}",
            headers=HEADERS,
            timeout=15,
        )
        current_sha = info.json().get("sha", "") if info.status_code == 200 else ""

        put = httpx.put(
            f"{API}/repos/{GITHUB_REPOSITORY}/contents/{file_path}",
            headers=HEADERS,
            json={
                "message": f"patchly: fix {Path(file_path).name}",
                "content": base64.b64encode(new_content.encode()).decode(),
                "sha": current_sha,
                "branch": branch_name,
            },
            timeout=15,
        )
        if put.status_code not in (200, 201):
            llm_log(f"  File write failed: {put.status_code}")
            return None
        llm_log("  File updated on branch")
    except Exception as e:
        llm_log(f"  File write error: {e}")
        return None

    pr = create_pr(
        title=f"Patchly: {issue.title[:72]}",
        body=f"Automated fix by Patchly.\n\n**Issue:** {issue.title}\n{issue.description}\n\n**File:** `{file_path}`",
        head=branch_name,
    )
    url = pr.get("html_url", "")
    llm_log(f"  PR created: {url}")
    return url
