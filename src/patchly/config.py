from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


PATCHLY_DIR = Path(os.environ.get("PATCHLY_DIR", ".patchly"))
WORKSPACE = Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd()))
EVENT_NAME = os.environ.get("GITHUB_EVENT_NAME", "")
EVENT_PATH = Path(os.environ.get("GITHUB_EVENT_PATH", "/dev/null"))
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "")
GITHUB_SHA = os.environ.get("GITHUB_SHA", "")


@dataclass
class AnalyzerConfig:
    enabled: bool = True
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class OllamaConfig:
    model: str = "qwen3-coder:30b"
    context_length: int = 32000
    flash_attention: bool = True
    kv_cache_type: str = "q8_0"
    num_thread: int = 4
    keep_alive: int = 300
    base_url: str = "http://localhost:11434"


@dataclass
class PatchlyConfig:
    mode: str = "review"
    provider: str = "api"
    model: str = "deepseek-v4-flash-free"
    api_base: str = "https://opencode.ai/zen/v1"
    api_key: str = "public"
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    auto_mode: str = "suggest"
    analyzers: dict[str, AnalyzerConfig] = field(default_factory=lambda: {
        name: AnalyzerConfig() for name in
        ["code_quality", "architecture", "performance", "modernization", "security"]
    })
    max_files_per_run: int = 20
    max_context_tokens: int = 32000
    comment_on_pr: bool = True
    auto_create_issues: bool = True
    auto_create_fix_prs: bool = False
    label_prefix: str = "patchly"


def load_event() -> dict[str, Any]:
    if EVENT_PATH.exists():
        return json.loads(EVENT_PATH.read_text())
    return {}


_CONFIG_CACHE: PatchlyConfig | None = None


def load_config(from_file: str | None = None) -> PatchlyConfig:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cfg = PatchlyConfig()

    config_file_env = os.environ.get("PATCHLY_CONFIG_FILE", "")
    if config_file_env and not from_file:
        from_file = config_file_env

    env_overrides = {
        "mode": "PATCHLY_MODE",
        "provider": "PATCHLY_PROVIDER",
        "model": "PATCHLY_MODEL",
        "api_base": "PATCHLY_API_BASE",
        "api_key": "PATCHLY_API_KEY",
        "auto_mode": "PATCHLY_AUTO_MODE",
        "comment_on_pr": "PATCHLY_COMMENT_ON_PR",
        "auto_create_issues": "PATCHLY_AUTO_CREATE_ISSUES",
        "auto_create_fix_prs": "PATCHLY_AUTO_CREATE_FIX_PRS",
        "max_files_per_run": "PATCHLY_MAX_FILES",
        "max_context_tokens": "PATCHLY_MAX_CONTEXT",
        "label_prefix": "PATCHLY_LABEL_PREFIX",
    }

    config_path = Path(from_file) if from_file else WORKSPACE / PATCHLY_DIR / "config.json"
    if config_path.exists():
        data = json.loads(config_path.read_text())
        for k, v in data.items():
            if k == "analyzers" and isinstance(v, dict):
                for aname, aopts in v.items():
                    if aname in cfg.analyzers:
                        if isinstance(aopts, bool):
                            cfg.analyzers[aname].enabled = aopts
                        elif isinstance(aopts, dict):
                            current = cfg.analyzers[aname]
                            for ak, av in aopts.items():
                                if hasattr(current, ak):
                                    setattr(current, ak, av)
            elif k == "ollama" and isinstance(v, dict):
                for ok, ov in v.items():
                    if hasattr(cfg.ollama, ok):
                        setattr(cfg.ollama, ok, ov)
            elif hasattr(cfg, k):
                setattr(cfg, k, v)

    for attr, env_key in env_overrides.items():
        val = os.environ.get(env_key)
        if val is not None:
            current = getattr(cfg, attr)
            if isinstance(current, bool):
                setattr(cfg, attr, val.lower() in ("1", "true", "yes"))
            elif isinstance(current, int):
                setattr(cfg, attr, int(val))
            else:
                setattr(cfg, attr, val)

    ollama_env_overrides = {
        "model": "PATCHLY_OLLAMA_MODEL",
        "context_length": "PATCHLY_OLLAMA_CONTEXT_LENGTH",
        "flash_attention": "PATCHLY_OLLAMA_FLASH_ATTENTION",
        "kv_cache_type": "PATCHLY_OLLAMA_KV_CACHE_TYPE",
        "num_thread": "PATCHLY_OLLAMA_NUM_THREAD",
        "keep_alive": "PATCHLY_OLLAMA_KEEP_ALIVE",
        "base_url": "PATCHLY_OLLAMA_BASE_URL",
    }
    for attr, env_key in ollama_env_overrides.items():
        val = os.environ.get(env_key)
        if val is not None:
            current = getattr(cfg.ollama, attr)
            if isinstance(current, bool):
                setattr(cfg.ollama, attr, val.lower() in ("1", "true", "yes"))
            elif isinstance(current, int):
                setattr(cfg.ollama, attr, int(val))
            else:
                setattr(cfg.ollama, attr, val)

    _CONFIG_CACHE = cfg
    return cfg


def reset_config_cache() -> None:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
