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
class ContextEngineConfig:
    max_files: int = 50
    include_dependencies: bool = True
    include_import_graph: bool = False
    diff_only_mode: bool = False


@dataclass
class SafeModeConfig:
    enabled: bool = True
    max_file_changes: int = 10
    require_diff_validation: bool = True
    block_destructive_changes: bool = True


@dataclass
class OutputsConfig:
    pr_comments: bool = True
    issues: bool = True
    patch_prs: bool = False
    reports: bool = True
    batch_fix_prs: bool = False


@dataclass
class OllamaConfig:
    model: str = "qwen3-coder:30b"
    quantization: str = "q3_k_m"
    gpu_layers: str = "auto"
    context_length: int = 32000
    flash_attention: bool = True
    kv_cache_type: str = "q8_0"
    num_thread: int = 4
    batch_size: int = 1024
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
    context_engine: ContextEngineConfig = field(default_factory=ContextEngineConfig)
    safe_mode: SafeModeConfig = field(default_factory=SafeModeConfig)
    outputs: OutputsConfig = field(default_factory=OutputsConfig)
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
    try:
        if EVENT_PATH.exists() and EVENT_PATH.stat().st_size > 0:
            raw = EVENT_PATH.read_text()
            if raw.strip():
                return json.loads(raw)
    except Exception:
        pass
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

    SUB_OBJECT_KEYS = {"analyzers", "ollama", "context_engine", "safe_mode", "outputs"}

    config_path = Path(from_file) if from_file else WORKSPACE / PATCHLY_DIR / "config.json"
    data: dict[str, Any] = {}
    if config_path.exists():
        data = json.loads(config_path.read_text())

    _apply_section(data, cfg, "context_engine", ContextEngineConfig)
    _apply_section(data, cfg, "safe_mode", SafeModeConfig)
    _apply_section(data, cfg, "outputs", OutputsConfig)

    if "analyzers" in data and isinstance(data["analyzers"], dict):
        for aname, aopts in data["analyzers"].items():
            if aname in cfg.analyzers:
                if isinstance(aopts, bool):
                    cfg.analyzers[aname].enabled = aopts
                elif isinstance(aopts, dict):
                    current = cfg.analyzers[aname]
                    for ak, av in aopts.items():
                        if hasattr(current, ak):
                            setattr(current, ak, av)

    if "ollama" in data and isinstance(data["ollama"], dict):
        for ok, ov in data["ollama"].items():
            if hasattr(cfg.ollama, ok):
                setattr(cfg.ollama, ok, ov)

    for k, v in data.items():
        if k not in SUB_OBJECT_KEYS and hasattr(cfg, k):
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
        "quantization": "PATCHLY_OLLAMA_QUANTIZATION",
        "gpu_layers": "PATCHLY_OLLAMA_GPU_LAYERS",
        "context_length": "PATCHLY_OLLAMA_CONTEXT_LENGTH",
        "flash_attention": "PATCHLY_OLLAMA_FLASH_ATTENTION",
        "kv_cache_type": "PATCHLY_OLLAMA_KV_CACHE_TYPE",
        "num_thread": "PATCHLY_OLLAMA_NUM_THREAD",
        "batch_size": "PATCHLY_OLLAMA_BATCH_SIZE",
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

    # Sync top-level auto_* flags with OutputsConfig sub-object when env var is set.
    # This ensures env var PATCHLY_AUTO_CREATE_ISSUES actually controls issue creation,
    # without overriding a config file's outputs.issues when the env var is absent.
    _auto_issues_env = os.environ.get("PATCHLY_AUTO_CREATE_ISSUES")
    if _auto_issues_env is not None:
        cfg.outputs.issues = _auto_issues_env.lower() in ("1", "true", "yes")
    _auto_fix_env = os.environ.get("PATCHLY_AUTO_CREATE_FIX_PRS")
    if _auto_fix_env is not None:
        cfg.outputs.patch_prs = _auto_fix_env.lower() in ("1", "true", "yes")
    _batch_fix_env = os.environ.get("PATCHLY_BATCH_FIX_PRS")
    if _batch_fix_env is not None:
        cfg.outputs.batch_fix_prs = _batch_fix_env.lower() in ("1", "true", "yes")

    return cfg


def _apply_section(
    data: dict[str, Any],
    cfg: PatchlyConfig,
    section_name: str,
    section_cls: type,
) -> None:
    section_data = data.get(section_name, {})
    if isinstance(section_data, dict):
        current = getattr(cfg, section_name, None)
        if current is None:
            current = section_cls()
        for k, v in section_data.items():
            if hasattr(current, k):
                if isinstance(getattr(current, k), bool) and not isinstance(v, bool):
                    setattr(current, k, str(v).lower() in ("1", "true", "yes"))
                else:
                    setattr(current, k, v)
        setattr(cfg, section_name, current)


def reset_config_cache() -> None:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
