# Trending Product Analyst — Product Vision

## What

A signal detector for the open-source community. Fetches trending and emerging projects from multiple sources, analyzes them through structured lenses, and produces research reports saved to a markdown knowledge base.

## Why

Smart people are building things in public. Most developers browse trending pages casually. The goal is to systematize this: understand not just *what* is trending, but *why* it matters, *why now*, and what larger shift it represents.

## Who

Primary user: you. A technical founder/developer who wants to stay sharp on ecosystem-level shifts without drowning in noise.

## Sources

- GitHub Trending (daily/weekly)
- Product Hunt (new launches)
- Hacker News (front-page discussion)
- Supplementary: curated awesome lists, high-star low-fork repos

## Signal Gate

Not every trending repo deserves a report. Filter before analysis:

- Star growth rate (velocity over raw count)
- Repository age (new projects are higher signal than mature ones gaining attention)
- Contributor diversity (first-time contributors indicate novelty, not just popularity)
- Retain signal metrics for later correlation

## Report Structure

Each report follows a standard template:

1. **TL;DR** — Two sentences: what this is and why it matters.
2. **What & Why** — The project's own narrative. What problem does it claim to solve?
3. **Technology Wave** — Which macro trend does this ride? What's the underlying force?
4. **Supply & Demand** — Why couldn't this exist two years ago? What changed?
5. **Product Analysis** — For what, for whom, business model.
6. **Creativity & Differentiation** — What's genuinely new vs. incremental? What existing solutions did the author reject and why?
7. **Competitive Landscape** — Who else solves this? Why might someone choose this instead?
8. **Community Signals** — Contributor mix, discussion quality, velocity indicators.
9. **Signal Assessment** — Real trend or temporary hype? Confidence level.
10. **Open Questions** — What's unclear. What to investigate next.

## Content Pipeline

```
Source API
  → Fetch (Python script, scheduled)
    → Signal Gate (cheap filter: star velocity, age, contributors)
      → Raw data collection (repo metadata, README, discussions)
        → Draft report (low-cost LLM)
          → Audit & enrich (flagship LLM)
            → Save to knowledge base
```

### Pipeline Details

- **Fetch & Gate**: Python script. Crude arithmetic filter, no LLM cost. Discards noise early.
- **Draft**: Low-cost LLM (GPT-4o-mini, Claude Haiku, etc.) generates a structured report from collected data.
- **Audit**: Flagship LLM (Claude Sonnet/Opus, GPT-4o) reviews draft, corrects errors, adds depth, flags weak analysis.
- **Knowledge Base**: `reports/` folder of markdown files. Filename pattern: `{date}-{source}-{project-name}.md`.

## Automation

- Standalone Python scripts, no web server needed.
- Scheduled via cron or a simple runner script.
- Configuration via `.env` or `config.yaml`.

## Principles

- **Signal over volume**: Better to produce fewer, higher-quality reports than to catalog everything.
- **Standardized structure**: Every report uses the same template. Consistency enables comparison over time.
- **Transparent reasoning**: Show confidence levels. Flag when analysis is speculative.
- **No decorative language**: The reports should be readable in 2 minutes and analytically dense.
- **Evolution-friendly**: The knowledge base grows. Future you can search it, compare trends across time, spot meta-patterns.
