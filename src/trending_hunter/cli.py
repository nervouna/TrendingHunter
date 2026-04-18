from __future__ import annotations

import click

from trending_hunter.config import load_config
from trending_hunter.fetchers.github import fetch_trending
from trending_hunter.gate import filter_projects
from trending_hunter.llm.tools import _clear_cache
from trending_hunter.log import get_logger, setup_logging
from trending_hunter.pipeline import run_pipeline
from trending_hunter.search import search_reports
from trending_hunter.settings import Settings


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--source", default="github", help="Data source to fetch from.")
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
@click.option("--dry-run", is_flag=True, help="Skip LLM calls and report writing.")
@click.option("--limit", default=0, type=int, help="Max number of repos to analyze (0 = all).")
def run(source: str, config_path: str, dry_run: bool, limit: int) -> None:
    setup_logging()
    log = get_logger()
    settings: Settings = load_config(config_path)

    if source == "github":
        gh = settings.sources.github

        log.info("Fetching GitHub trending (language=%s, since=%s)", gh.language, gh.since)
        repos = fetch_trending(language=gh.language, since=gh.since, proxy=settings.proxy or None)
        click.echo(f"Fetched {len(repos)} trending repos")

        passed = filter_projects(repos, settings.signal_gate)
        click.echo(f"Passed signal gate: {len(passed)}/{len(repos)}")

        if limit > 0:
            passed = passed[:limit]
            click.echo(f"Limited to {len(passed)} repo(s)")

        if dry_run:
            for r in passed:
                vel = f"{r.star_velocity:.1f}" if r.star_velocity else "n/a"
                click.echo(f"  {r.name} | {r.stars} stars | {vel}/day")
            return

        _clear_cache()
        results = run_pipeline(passed, settings)

        for i, r in enumerate(results):
            click.echo(f"\n[{i+1}/{len(results)}] {r.project.name}")
            if r.error:
                click.echo(f"  ERROR: {r.error}")
            else:
                for stage in ("draft", "audit", "rewrite"):
                    tokens = r.token_usage.get(stage, {})
                    click.echo(f"  {stage.title()}: {tokens.get('input', 0)}+{tokens.get('output', 0)} tokens")
                click.echo(f"  Saved: {r.file_path}")
                click.echo(f"  Cost: ${r.cost:.4f}")

    else:
        click.echo(f"Source '{source}' not yet implemented.")


@cli.command()
@click.option("--keyword", default=None, help="Search keyword.")
@click.option("--source", default=None, help="Filter by source.")
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
def search(keyword: str | None, source: str | None, config_path: str) -> None:
    settings: Settings = load_config(config_path)
    kb_path = settings.knowledge_base.path

    results = search_reports(base_dir=kb_path, keyword=keyword, source=source)

    if not results:
        click.echo("No matching reports found.")
        return

    click.echo(f"Found {len(results)} report(s):")
    for filename, excerpt in results:
        click.echo(f"\n  {filename}")
        click.echo(f"    {excerpt}...")
