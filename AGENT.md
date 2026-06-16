# Patchly Agent — Operating Contract

Any agent (human or autonomous) working on Patchly MUST follow this contract.

## CRITICAL RULES

1. **ALWAYS update the version** in `VERSION` file and `src/patchly/__init__.py` when making changes. Follow semver:
   - MAJOR: breaking changes
   - MINOR: new features
   - PATCH: bug fixes
2. **ALWAYS run all tests** before committing: `PYTHONPATH=src python3 -m pytest tests/`
3. **ALWAYS check CI** after pushing — ensure the workflow passes on the repo

## Architecture

```
Event → Context Builder → Web Sanitizer → Memory Injection
                                              ↓
                         Analysis → Risk Scoring → Action Decision
                                                       ↓
                              Patch → Verification Loop → PR/Comment/Abort
```

### Pipeline stages

1. **Event trigger** — PR, schedule, issue comment, workflow_dispatch
2. **Context builder** — Repository files enumerated, relevant files selected
3. **Web sanitizer** — URLs fetched and sanitized (anti-prompt-injection)
4. **Memory injection** — Past decisions, patterns, known issues injected into LLM context
5. **Analysis** — Multi-dimensional analysis (code quality, architecture, performance, modernization, security)
6. **Risk scoring** — Each finding scored: 0-1=comment, 2-3=PR, 4+=human review
7. **Action decision** — Comment, create PR, or flag for human review
8. **Patch** — Auto-generate fixes with SEARCH/REPLACE blocks
9. **Verification loop** — Patch → verify → retry (max 3 cycles)
10. **Report** — Timestamped JSON written to `.patchly/reports/`

## Modules

| Path | Purpose |
|------|---------|
| `src/patchly/__init__.py` | Package init, version (read from VERSION) |
| `src/patchly/__main__.py` | CLI entry point |
| `src/patchly/agent.py` | Main orchestrator with full pipeline |
| `src/patchly/config.py` | Configuration with context_engine, safe_mode, outputs, ollama sections |
| `src/patchly/context.py` | Repository context builder |
| `src/patchly/llm.py` | LLM abstraction with progressive logging |
| `src/patchly/github_client.py` | GitHub API client with dynamic default branch detection |
| `src/patchly/web.py` | URL fetcher with prompt injection sanitizer |
| `src/patchly/memory.py` | Repo memory (decisions, patterns, known issues, module rules) |
| `src/patchly/risk.py` | Risk scoring engine |
| `src/patchly/safe_mode.py` | Concrete safe mode rules |
| `src/patchly/analyzers/` | Analysis modules |
| `src/patchly/actions/` | Action modules (ActionResult, PR creation) |
| `src/patchly/modes/` | Mode entry points (review, scan, fix, continuous, command) |
| `src/patchly/utils/` | Utility modules (patterns, validation) |

## Provider architecture

- **`api`** — OpenCode API, OpenAI-compatible endpoints. Set `api_base` to any OpenAI-compatible URL.
- **`ollama`** — Local models via Ollama. Configured for Qwen3-Coder with flash attention, q8_0 KV cache.

## Configuration priority

1. `.patchly/config.json`
2. `PATCHLY_*` environment variables
3. Defaults in `PatchlyConfig` dataclass

## Modes

| Mode | Description |
|------|-------------|
| `review` | Analyze PR diffs, post structured review comments |
| `scan` | Full repository scan for issues |
| `fix` | Auto-generate patches, verify, create PRs |
| `continuous` | Incremental maintenance over time |
| `command` | Respond to `/patchly <cmd>` in issues/comments |

## Security rules

- Never modify `.patchly/`, `.git/`, `.env`, or `.github/workflows/`
- Auto-changes go through PRs, never direct to default branch
- Safe mode blocks: auth logic, CI/CD, secrets, Docker, >10 files
- Web content is sanitized for prompt injection before LLM ingestion
- Risk scoring prevents high-risk changes from being automated
