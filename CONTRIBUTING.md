# Contributing

## Development setup

```bash
git clone https://github.com/Llucs/patchly
cd patchly
pip install httpx
```

## Project structure

```
src/patchly/          # Core library
  agent.py            # Main orchestrator
  config.py           # Configuration
  context.py          # Context building
  llm.py              # LLM abstraction
  github_client.py    # GitHub API
  analyzers/          # Analysis modules
  actions/            # Action modules
  modes/              # Mode entry points
  utils/              # Utilities
tests/                # Test suite
.patchly/             # Default configuration
.github/workflows/    # CI workflows
```

## Adding an analyzer

1. Create a new file in `src/patchly/analyzers/`
2. Subclass `BaseAnalyzer` and implement `analyze(files) -> list[ActionResult]`
3. Register it in `src/patchly/analyzers/__init__.py`

## Adding a provider

1. Add a new `_<provider>_chat()` function in `src/patchly/llm.py`
2. Add a routing branch in the `chat()` function
3. Add provider config fields in `PatchlyConfig`

## Running tests

```bash
python -m pytest tests/
```

## Code style

- Python 3.11+ type annotations everywhere
- No external dependencies beyond `httpx`
- No docstrings or comments in source code
- Everything in English
