from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any

import httpx

from patchly.config import PatchlyConfig


PATCHLY_SYSTEM_PROMPT = """You are Patchly, an autonomous software engineering agent operating inside a GitHub repository.

Your purpose is to analyze, maintain, and improve the codebase continuously.

## Modes

### review
Review pull request changes. Analyze diffs for bugs, style issues, security problems, architectural impact, and test coverage. Provide actionable feedback.

### scan
Scan the entire repository for issues. Look for deprecated APIs, performance problems, duplicated code, overly complex functions, architectural smells, and security vulnerabilities.

### fix
Generate patches for detected issues. After fixing, verify the change is correct.

### continuous
Incremental repository maintenance. Track changes over time, fix small issues, modernize patterns gradually.

### command
Respond to direct developer commands via /patchly in issues or comments.

## Analysis scope

When analyzing code, consider:
1. Code quality — complexity, duplication, naming, error handling
2. Architecture — coupling, cohesion, dependency direction, layering
3. Performance — N+1 queries, unnecessary allocations, cache opportunities
4. Modernization — deprecated APIs, outdated patterns, version upgrades
5. Security — injection flaws, auth issues, secret exposure

## Response format

Always structure responses with clear sections. Use Markdown formatting. Include specific file paths and line numbers when referencing code. Explain why something is a problem and how to fix it.

Be direct and technical. No unnecessary preamble. No placeholders. Every claim must be backed by specific code evidence."""


def log(msg: str) -> None:
    print(f"  ▶ {msg}", flush=True)


def divider() -> None:
    print("  " + "─" * 60, flush=True)


def chat(
    messages: list[dict[str, str]],
    config: PatchlyConfig,
    system: str | None = None,
) -> str:
    full = [{"role": "system", "content": system or PATCHLY_SYSTEM_PROMPT}]
    full.extend(messages)

    log("Sending request to LLM...")
    if config.provider == "ollama":
        return _ollama_chat(full, config)
    return _api_chat(full, config)


def _api_chat(
    messages: list[dict[str, str]],
    config: PatchlyConfig,
    max_retries: int = 3,
    timeout: int = 300,
) -> str:
    for attempt in range(1, max_retries + 1):
        if attempt > 1:
            log(f"Retry attempt {attempt}/{max_retries}...")
        try:
            resp = httpx.post(
                f"{config.api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": config.model,
                    "messages": messages,
                    "stream": False,
                },
                timeout=timeout,
            )
            if resp.status_code == 500:
                log("Server error, retrying...")
                time.sleep(5)
                continue
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            divider()
            print(content, flush=True)
            divider()
            return content
        except Exception as e:
            log(f"API error: {e}")
            if attempt < max_retries:
                time.sleep(5)
    raise RuntimeError("API call failed after retries")


def _ollama_chat(
    messages: list[dict[str, str]],
    config: PatchlyConfig,
) -> str:
    cfg = config.ollama
    payload = {
        "model": cfg.model,
        "messages": messages,
        "options": {
            "num_ctx": cfg.context_length,
            "num_thread": cfg.num_thread,
        },
        "keep_alive": f"{cfg.keep_alive}s",
        "stream": False,
    }

    env = os.environ.copy()
    if cfg.flash_attention:
        env["OLLAMA_FLASH_ATTENTION"] = "1"
    if cfg.kv_cache_type:
        env["OLLAMA_KV_CACHE_TYPE"] = cfg.kv_cache_type

    for attempt in range(3):
        try:
            resp = httpx.post(
                f"{cfg.base_url}/api/chat",
                json=payload,
                timeout=600,
            )
            if resp.status_code == 200:
                content = resp.json()["message"]["content"].strip()
                divider()
                print(content, flush=True)
                divider()
                return content
            log(f"Ollama error (status {resp.status_code}), retrying...")
            time.sleep(5)
        except httpx.ConnectError:
            if attempt == 0:
                log("Starting Ollama server...")
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                )
                time.sleep(10)
            else:
                time.sleep(5)

    raise RuntimeError("Ollama call failed after retries")
