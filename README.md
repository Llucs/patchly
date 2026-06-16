# Patchly

Autonomous software engineering agent that lives inside GitHub repositories. Patchly acts as an intelligent, continuous maintainer — reviewing code, detecting issues, fixing bugs, modernizing patterns, and evolving the codebase over time.

## How it works

Patchly runs inside GitHub Actions and responds to repository events: pull requests, scheduled scans, issues, and direct commands. It builds a contextual understanding of the repository, runs analysis pipelines across multiple dimensions, and takes action — commenting on PRs, opening issues, or creating fix PRs.

```
Repository event → Context builder → Analysis pipeline → Actions
                        ↓                    ↓               ↓
                 File listing        Code quality       PR comment
                 Dependency map     Architecture       Issue report
                 Change diff        Performance        Fix PR
                                    Modernization
                                    Security
```

## Modes

### `review`
Triggered automatically on pull requests. Analyzes the diff for bugs, code quality, architecture impact, performance regressions, and security vulnerabilities. Posts a structured review comment on the PR.

### `scan`
Runs on a schedule or manually. Scans the entire repository looking for deprecated patterns, code duplication, overly complex functions, architectural smells, performance bottlenecks, and security issues. Results can be reported as issues or saved as reports.

### `command`
Responds to developer commands posted in issues or comments. Commands use the format `/patchly <instruction>` — for example `/patchly refactor the auth module` or `/patchly find performance issues in database queries`.

## Configuration

Patchly is configured through `.patchly/config.json` in the repository root. All settings have sensible defaults and can be overridden via environment variables.

```json
{
  "provider": "api",
  "model": "deepseek-v4-flash-free",
  "api_base": "https://opencode.ai/zen/v1",
  "auto_mode": "suggest",
  "comment_on_pr": true,
  "auto_create_issues": true,
  "auto_create_fix_prs": false,
  "analyzers": {
    "code_quality": {"enabled": true},
    "architecture": {"enabled": true},
    "performance": {"enabled": true},
    "modernization": {"enabled": false},
    "security": {"enabled": true}
  },
  "ollama": {
    "model": "qwen3-coder:30b",
    "context_length": 32000,
    "flash_attention": true,
    "kv_cache_type": "q8_0",
    "num_thread": 4
  }
}
```

### Provider selection

Set `"provider": "api"` to use cloud LLMs via the OpenCode API (free, no key needed). Set `"provider": "ollama"` to use a local model running on the CI runner. Environment variable override: `PATCHLY_PROVIDER=ollama`.

### Environment variables

| Variable | Description |
|----------|-------------|
| `PATCHLY_PROVIDER` | `api` or `ollama` |
| `PATCHLY_MODEL` | Model name for API provider |
| `PATCHLY_API_BASE` | API base URL |
| `PATCHLY_MODE` | `review`, `scan`, or `command` |
| `PATCHLY_AUTO_MODE` | `suggest` or `auto` |
| `PATCHLY_OLLAMA_MODEL` | Ollama model tag |
| `PATCHLY_OLLAMA_CONTEXT_LENGTH` | Context window in tokens |
| `PATCHLY_OLLAMA_FLASH_ATTENTION` | Enable flash attention |
| `PATCHLY_OLLAMA_KV_CACHE_TYPE` | KV cache quantization |
| `PATCHLY_OLLAMA_NUM_THREAD` | CPU threads for inference |

## Workflows

### PR review workflow

Add `.github/workflows/patchly-pr-review.yml` to your repository:

```yaml
name: patchly review
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install httpx
      - run: |
          curl -sL https://github.com/Llucs/patchly/archive/main.tar.gz | tar xz --strip=1 patchly-main/src/patchly
      - run: python -m patchly
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          GITHUB_EVENT_NAME: ${{ github.event_name }}
          GITHUB_EVENT_PATH: ${{ github.event_path }}
```

### Scheduled scan workflow

```yaml
name: patchly scan
on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install httpx
      - run: |
          curl -sL https://github.com/Llucs/patchly/archive/main.tar.gz | tar xz --strip=1 patchly-main/src/patchly
      - run: python -m patchly --mode=scan
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
```

### Running with Ollama locally

```yaml
name: patchly local
on:
  workflow_dispatch:
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: |
          curl -fsSL https://ollama.com/install.sh | sh
          ollama pull qwen3-coder:30b
        env:
          OLLAMA_FLASH_ATTENTION: "1"
          OLLAMA_KV_CACHE_TYPE: "q8_0"
      - uses: actions/cache@v4
        with:
          path: ~/.ollama
          key: ollama-${{ hashFiles('~/.ollama/models/*') }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install httpx
      - run: |
          curl -sL https://github.com/Llucs/patchly/archive/main.tar.gz | tar xz --strip=1 patchly-main/src/patchly
      - run: python -m patchly --mode=scan
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          PATCHLY_PROVIDER: ollama
          PATCHLY_MODE: scan
```

## Requirements

- **API mode**: No local hardware requirements. Works with any GitHub-hosted runner.
- **Ollama mode**: CI runner with ~16GB RAM for Qwen3-Coder 30B (Q3_K_M quantization with optimizations). First run downloads ~15GB model; subsequent runs use GitHub Actions cache.
- Python 3.11+
- `httpx` library

## License

Apache 2.0
