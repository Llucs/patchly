# Patchly Agent

Operating contract for any agent (human or autonomous) working on Patchly.

## Architecture

Patchly follows a pipeline architecture:

1. **Event trigger** — GitHub event arrives (PR, schedule, issue comment, workflow_dispatch)
2. **Context building** — Repository files are enumerated, relevant files are selected
3. **Analysis pipeline** — Multiple analyzers run (code quality, architecture, performance, modernization, security)
4. **Action execution** — Results are dispatched as PR comments, issues, or fix PRs
5. **Report generation** — A timestamped report is written to `.patchly/reports/`

## Provider architecture

Patchly supports two LLM providers:

- **`api`** (default) — Uses the OpenCode API with `deepseek-v4-flash-free`. No API key required. Free. Cloud-hosted. 200K context.
- **`ollama`** — Uses a local model via Ollama running on the CI runner. Configured for Qwen3-Coder 30B-A3B with flash attention, KV cache quantization, and optimized thread count.

Both providers implement the same `chat()` interface and are interchangeable via configuration.

## Configuration priority

1. `.patchly/config.json` in the repository root
2. Environment variables (`PATCHLY_*`)
3. Default values in `PatchlyConfig`

## Mode behavior

- **review** — Reads `GITHUB_EVENT_PATH` for pull request payload, fetches diff via API, analyzes, comments
- **scan** — Walks repository source files, runs analyzers, optionally opens issues
- **command** — Reads issue/comment body for `/patchly` command, executes and responds

## Security

- Never modify `.patchly/`, `.git/`, or `.env` files
- All auto-generated changes go through PRs, never direct pushes to main
- `auto_mode: suggest` only comments; `auto_mode: auto` can create fix PRs
- GitHub token permissions should be limited to `contents: write` and `pull-requests: write`

## Files

| Path | Purpose |
|------|---------|
| `src/patchly/__init__.py` | Package init, version |
| `src/patchly/__main__.py` | CLI entry point |
| `src/patchly/agent.py` | Main orchestrator |
| `src/patchly/config.py` | Configuration loading |
| `src/patchly/context.py` | Repository context |
| `src/patchly/llm.py` | LLM abstraction layer |
| `src/patchly/github_client.py` | GitHub API client |
| `src/patchly/analyzers/` | Analysis modules |
| `src/patchly/actions/` | Action modules |
| `src/patchly/modes/` | Mode entry points |
| `src/patchly/utils/` | Utility modules |
