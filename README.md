# TrendingHunter

Automated pipeline that discovers trending open-source projects and generates analytical reports using LLMs.

Fetches from GitHub Trending, Product Hunt, and Hacker News, filters by signal (star velocity, repo age), then runs a 3-stage LLM pipeline (Draft → Audit → Rewrite) to produce structured Markdown reports.

## Quick Start

```bash
# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure
cp config.example.yaml config.yaml
cp .env.example .env
# Edit config.yaml (models, thresholds) and .env (API keys)

# Run a single pipeline
th run --source github --limit 3

# Run with Chinese output
th run --source github --limit 3 -l chinese

# Schedule periodic runs (every hour)
th schedule --interval 3600

# Search existing reports
th search --keyword "AI"
```

## CLI

| Command | Description |
|---------|-------------|
| `th run` | Single fetch-filter-analyze cycle |
| `th schedule` | Periodic runs with configurable interval |
| `th search` | Search reports by keyword or source |

**`th run` options:**

- `--source` — `github`, `product_hunt`, or `hacker_news` (default: `github`)
- `--limit` — max projects to analyze (default: 0 = all)
- `--language`, `-l` — output report language (e.g. `chinese`, `japanese`)
- `--dry-run` — fetch and filter only, skip LLM calls
- `--config` — path to config file (default: `config.yaml`)

## How It Works

```
Fetcher → Signal Gate → LLM Pipeline → Writer
```

1. **Fetch** — pull trending projects from configured sources
2. **Filter** — signal gate drops projects below thresholds (star velocity, repo age)
3. **Draft** — LLM generates initial 11-section analysis from project data + web research
4. **Audit** — second LLM fact-checks the draft using Tavily web search
5. **Rewrite** — third LLM polishes into clean prose
6. **Save** — Markdown report saved to `./reports/`

Reports are idempotent: existing reports for the same project+date are skipped.

## Configuration

`config.yaml` controls sources, signal gate thresholds, LLM endpoints, and pricing. Start from `config.example.yaml`:

```bash
cp config.example.yaml config.yaml
```

Secrets are stored in `.env` (gitignored) and referenced via `${VAR_NAME}` syntax in `config.yaml`. The config loader also supports `TH_*` env var overrides — any config key can be overridden without editing YAML (e.g. `TH_LLM_DRAFT_MODEL=gpt-4o`).

Required env vars:

| Variable | Purpose |
|----------|---------|
| `TH_DRAFT_BASE_URL` | Draft LLM API base URL |
| `TH_DRAFT_API_KEY` | Draft LLM API key |
| `TH_AUDIT_BASE_URL` | Audit LLM API base URL |
| `TH_AUDIT_API_KEY` | Audit LLM API key |
| `TH_REWRITE_BASE_URL` | Rewrite LLM API base URL |
| `TH_REWRITE_API_KEY` | Rewrite LLM API key |
| `TH_TAVILY_API_KEY` | Tavily web search API key |
| `TH_PRODUCTHUNT_TOKEN` | Product Hunt API token |

## Development

```bash
python -m pytest tests/ -v          # all tests
python -m pytest tests/test_cli.py -v  # single file
```
