from __future__ import annotations

import time
from collections.abc import Callable

import click

from trending_hunter.config import load_config
from trending_hunter.fetchers.github import fetch_trending
from trending_hunter.fetchers.producthunt import fetch_producthunt
from trending_hunter.fetchers.hackernews import fetch_hackernews
from trending_hunter.gate import filter_projects
from trending_hunter.llm.tools import _clear_cache
from trending_hunter.log import get_logger, setup_logging
from trending_hunter.models import Project
from trending_hunter.pipeline import run_pipeline
from trending_hunter.search import search_reports
from trending_hunter.settings import Settings

_FETCHERS: dict[str, Callable[..., list[Project]]] = {
    "github": fetch_trending,
    "product_hunt": fetch_producthunt,
    "hacker_news": fetch_hackernews,
}


def run_cycle(source: str, config_path: str, limit: int, dry_run: bool) -> None:
    log = get_logger()
    settings: Settings = load_config(config_path)

    fetcher = _FETCHERS.get(source)
    if fetcher is None:
        click.echo(f"Unknown source: '{source}'. Available: {', '.join(_FETCHERS)}")
        return

    try:
        source_config = getattr(settings.sources, source)
    except AttributeError:
        click.echo(f"No configuration found for source '{source}'")
        return

    if not getattr(source_config, 'enabled', True):
        click.echo(f"Source '{source}' is disabled.")
        return

    kwargs: dict[str, object] = {"proxy": settings.proxy or None}
    if source == "github":
        kwargs['language'] = source_config.language
        kwargs['since'] = source_config.since
        log.info("Fetching GitHub trending (language=%s, since=%s)", source_config.language, source_config.since)
    elif source == "hacker_news":
        kwargs['top_n'] = source_config.top_n
    elif source == "product_hunt":
        kwargs['token'] = source_config.token
        kwargs['top_n'] = source_config.top_n

    try:
        repos = fetcher(**kwargs)
    except NotImplementedError as exc:
        click.echo(str(exc))
        return

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
        elif r.status == "skipped":
            click.echo(f"  SKIPPED: {r.file_path} (already exists)")
        else:
            for stage in ("draft", "audit", "rewrite"):
                tokens = r.token_usage.get(stage)
                if tokens:
                    click.echo(f"  {stage.title()}: {tokens.input_tokens}+{tokens.output_tokens} tokens")
            click.echo(f"  Saved: {r.file_path}")
            click.echo(f"  Cost: ${r.cost:.4f}")


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
    run_cycle(source, config_path, limit, dry_run)


@cli.command()
@click.option("--source", default="github", help="Data source to fetch from.")
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
@click.option("--limit", default=0, type=int, help="Max number of repos to analyze (0 = all).")
@click.option("--interval", default=3600, type=int, help="Seconds between runs.")
@click.option("--cycles", default=0, type=int, help="Max cycles (0 = infinite).")
def schedule(source: str, config_path: str, limit: int, interval: int, cycles: int) -> None:
    setup_logging()
    cycle = 0
    while cycles == 0 or cycle < cycles:
        cycle += 1
        click.echo(f"\n--- Cycle {cycle} ---")
        run_cycle(source, config_path, limit, dry_run=False)
        if cycles == 0 or cycle < cycles:
            time.sleep(interval)


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
