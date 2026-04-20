# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
python3 -m venv .venv               # create venv
source .venv/bin/activate           # activate venv
pip install -e ".[dev]"             # install with dev deps
th run --source github -l chinese   # single pipeline run
th schedule --interval 3600         # periodic runs
python -m pytest tests/ -v          # run all tests
python -m pytest tests/test_cli.py -v  # single file
```

## Architecture

Pipeline: `fetcher → gate → LLM (draft → audit → rewrite) → writer`

- `src/trending_hunter/cli.py` — Click CLI, dispatches to `run_cycle`
- `src/trending_hunter/pipeline.py` — orchestrates the 3-stage LLM pipeline per project
- `src/trending_hunter/llm/` — draft, audit, rewrite stages; prompts in `prompts.py`
- `src/trending_hunter/fetchers/` — github, producthunt, hackernews data sources
- `src/trending_hunter/gate.py` — signal gate filtering (star velocity, repo age)
- `src/trending_hunter/writer.py` — renders Report to Markdown, saves to `./reports/`

## Workflow

1. TDD: red-green-refactor. Write failing tests first, then implement, then clean up.
2. Run `/simplify` before each commit.
3. Commit in minimal logical batches — one commit per logical change.

## Code Style

- Python 3.11+, `from __future__ import annotations` in all modules
- Type hints everywhere; Pydantic v2 for models and settings
- No comments unless documenting non-obvious constraints
- All identifiers and comments in English
- Tests: `unittest.mock.patch` for isolation, `click.testing.CliRunner` for CLI tests

## Config & Secrets

- Runtime config: `config.yaml` (gitignored, Pydantic-validated via `settings.py`)
- Example config: `config.example.yaml` — copy and customize
- Secrets via env vars (`.env` file supported, gitignored):
  - `TH_DRAFT_BASE_URL`, `TH_DRAFT_API_KEY`
  - `TH_AUDIT_BASE_URL`, `TH_AUDIT_API_KEY`
  - `TH_REWRITE_BASE_URL`, `TH_REWRITE_API_KEY`
  - `TH_TAVILY_API_KEY`, `TH_PRODUCTHUNT_TOKEN`
- Env var resolution: `${VAR_NAME}` syntax in `config.yaml` is expanded by `config.py`
- Override any config key via `TH_` prefix env vars (e.g. `TH_LLM_DRAFT_MODEL=...`)
