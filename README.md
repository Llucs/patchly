# Patchly (WIP)

Autonomous software engineering agent inside GitHub repositories.
Connects to almost any LLM — cloud APIs or local models.

### We need contributors; this project is constantly evolving!

## How it works

Patchly runs as a GitHub Action triggered by repository events. It builds context, runs multi-dimensional analysis, and acts on findings — reviewing PRs, scanning for issues, fetching web docs, creating fix PRs, and continuously maintaining the codebase.

```
Event → Context Builder → Analysis Pipeline → Actions
                             │                    │
                    ┌────────┼────────┐    ┌──────┴──────┐
                    │        │        │    │             │
              Code Quality  Security   │  PR Comment   Fix PR
              Architecture  Perf      │  Issue Report Auto-Patch
              Modernization Web Docs  │  Branch       Commit
```

## Modes

### `review`
Triggered on pull requests. Analyzes diffs for bugs, quality, architecture, performance, security. Posts structured review comments.

### `scan`
Scheduled or manual. Scans the full repo for deprecated patterns, code duplication, complex functions, architectural issues, and security vulnerabilities. Can open issues or generate reports.

### `fix`
Auto-generates patches for detected issues. Creates branches, applies fixes, and opens pull requests — fully autonomous or with human review.

### `continuous`
Incremental repository maintenance over time. Tracks file modification dates and processes the codebase in small batches, fixing issues and modernizing patterns across many runs.

### `command`
Responds to `/patchly <instruction>` commands from issues or comments. Supports any natural language instruction.

### `web`
Fetches external documentation and resources during analysis. URLs mentioned in issues, PRs, or detected by analyzers are automatically retrieved and included in context.

## Configuration

Patchly is configured through `.patchly/config.json`. All settings have sensible defaults and can be overridden via `PATCHLY_*` environment variables.

```json
{
  "provider": "api",
  "model": "deepseek-v4-flash-free",
  "context_engine": {
    "max_files": 50,
    "include_dependencies": true,
    "include_import_graph": false,
    "diff_only_mode": false
  },
  "safe_mode": {
    "enabled": true,
    "max_file_changes": 10,
    "require_diff_validation": true,
    "block_destructive_changes": true
  },
  "outputs": {
    "pr_comments": true,
    "issues": true,
    "patch_prs": false,
    "reports": true
  },
  "ollama": {
    "model": "qwen3-coder:30b",
    "quantization": "q3_k_m",
    "gpu_layers": "auto",
    "context_length": 32000,
    "flash_attention": true,
    "kv_cache_type": "q8_0",
    "num_thread": 4,
    "batch_size": 1024
  },
  "analyzers": {
    "code_quality": { "enabled": true },
    "architecture": { "enabled": true },
    "performance": { "enabled": true },
    "modernization": { "enabled": false },
    "security": { "enabled": true }
  }
}
```

### Provider selection

Supports any LLM provider via two modes:

| Provider | Setting | Description |
|----------|---------|-------------|
| **API** | `"provider": "api"` | Cloud LLMs (OpenCode, OpenAI, Anthropic, DeepSeek, OpenRouter, etc.) |
| **Ollama** | `"provider": "ollama"` | Local models on the CI runner (Qwen3, DeepSeek, Llama, etc.) |

Set `api_base` to point to any OpenAI-compatible endpoint. Works with OpenCode, OpenAI, Anthropic via proxy, DeepSeek, Groq, OpenRouter, Together, Fireworks, and any custom endpoint.

### Environment variables

| Variable | Description |
|----------|-------------|
| `PATCHLY_PROVIDER` | `api` or `ollama` |
| `PATCHLY_MODEL` | Model name for API provider |
| `PATCHLY_API_BASE` | API base URL |
| `PATCHLY_MODE` | `review`, `scan`, `fix`, `continuous`, or `command` |
| `PATCHLY_AUTO_MODE` | `suggest` or `auto` |
| `PATCHLY_OLLAMA_MODEL` | Ollama model tag |
| `PATCHLY_OLLAMA_QUANTIZATION` | Quantization level (q3_k_m, q4, q8_0, etc.) |
| `PATCHLY_OLLAMA_GPU_LAYERS` | GPU layers (`auto` to detect, `0` for CPU-only) |
| `PATCHLY_OLLAMA_BATCH_SIZE` | Batch size for prompt processing |

## Workflows

### PR review

```yaml
- uses: Llucs/patchly@main
  with:
    mode: review
```

### Scheduled scan

```yaml
- uses: Llucs/patchly@main
  with:
    mode: scan
```

### Fix mode (auto-patch)

```yaml
- uses: Llucs/patchly@main
  with:
    mode: fix
    auto_create_fix_prs: true
```

### Continuous maintenance

```yaml
- uses: Llucs/patchly@main
  with:
    mode: continuous
```

### Local model (Ollama)

```yaml
- uses: Llucs/patchly@main
  with:
    provider: ollama
    mode: scan
```

## Requirements

- **API mode**: No local hardware. Works on any GitHub-hosted runner.
- **Ollama mode**: ~16GB RAM for Qwen3-Coder 30B (Q3_K_M). First run downloads ~15GB model.
- Python 3.11+
- `httpx` library

## Required permissions

Your workflow must include the following permissions for Patchly features:

```yaml
permissions:
  contents: write       # fix mode (branches, commits)
  pull-requests: write  # review & command mode (comments)
  issues: write         # scan mode (creating issues)
```

Without the correct permissions, Patchly will log a clear error instead of crashing.

## License

Apache 2.0
