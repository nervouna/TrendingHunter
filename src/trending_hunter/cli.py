from __future__ import annotations

import signal
import threading
import time
from collections.abc import Callable
from typing import TypeVar

import click

from trending_hunter.config import load_config
from trending_hunter.dedup import SeenUrls
from trending_hunter.fetchers.base import Fetcher
from trending_hunter.fetchers.github import GitHubFetcher
from trending_hunter.fetchers.hackernews import HackerNewsFetcher
from trending_hunter.fetchers.producthunt import ProductHuntFetcher
from trending_hunter.gate import filter_projects
from trending_hunter.log import get_logger, setup_logging
from trending_hunter.models import Source
from trending_hunter.pipeline import run_pipeline
from trending_hunter.search import search_reports
from trending_hunter.settings import Settings

_shutdown_event = threading.Event()
_consecutive_failures = 0
_MAX_BACKOFF = 300  # 5 minutes
_F = TypeVar("_F", bound=Callable[..., object])

_FETCHERS: dict[str, Fetcher] = {
    "github": GitHubFetcher(),
    "product_hunt": ProductHuntFetcher(),
    "hacker_news": HackerNewsFetcher(),
}


def _resolve_fetcher_args(
    source: str,
    settings: Settings,
) -> tuple[Fetcher | None, str | None]:
    fetcher = _FETCHERS.get(source)
    if fetcher is None:
        return None, f"Unknown source: '{source}'. Available: {', '.join(_FETCHERS)}"

    try:
        source_config = getattr(settings.sources, source)
    except AttributeError:
        return None, f"No configuration found for source '{source}'"

    if not getattr(source_config, "enabled", True):
        return None, f"Source '{source}' is disabled."

    return fetcher, None


def run_cycle(
    source: str,
    config_path: str,
    limit: int,
    dry_run: bool,
    language: str = "",
    skip_rewrite: bool = False,
) -> None:
    log = get_logger()
    settings: Settings = load_config(config_path)

    fetcher, error = _resolve_fetcher_args(source, settings)
    if error is not None:
        click.echo(error)
        return
    if fetcher is None:
        click.echo(f"Unknown source: '{source}'.")
        return

    if source == "github":
        log.info(
            "Fetching GitHub trending (language=%s, since=%s)",
            settings.sources.github.language,
            settings.sources.github.since,
        )

    try:
        repos = fetcher.fetch(settings)
    except NotImplementedError as exc:
        click.echo(str(exc))
        return
    except Exception as exc:
        click.echo(f"Fetcher error ({source}): {exc}")
        return

    click.echo(f"Fetched {len(repos)} trending repos")

    passed = filter_projects(repos, settings.signal_gate, source=Source(source))
    click.echo(f"Passed signal gate: {len(passed)}/{len(repos)}")

    if limit > 0:
        passed = passed[:limit]
        click.echo(f"Limited to {len(passed)} repo(s)")

    if dry_run:
        for project in passed:
            vel = f"{project.star_velocity:.1f}" if project.star_velocity else "n/a"
            click.echo(f"  {project.name} | {project.stars} stars | {vel}/day")
        return

    seen = SeenUrls(f"{settings.knowledge_base.path}/.seen_urls.json")
    seen.load()
    results = run_pipeline(
        passed, settings, language=language, seen=seen, skip_rewrite=skip_rewrite
    )

    for i, result in enumerate(results):
        click.echo(f"\n[{i + 1}/{len(results)}] {result.project.name}")
        if result.error:
            click.echo(f"  ERROR: {result.error}")
        elif result.status == "skipped":
            click.echo(f"  SKIPPED: {result.file_path} (already exists)")
        else:
            for stage in ("draft", "audit", "rewrite"):
                tokens = result.token_usage.get(stage)
                if tokens:
                    token_summary = (
                        f"{tokens.input_tokens}+{tokens.output_tokens} tokens"
                    )
                    click.echo(f"  {stage.title()}: {token_summary}")
            if result.file_path:
                click.echo(f"  Saved: {result.file_path}")
            if result.run_id:
                click.echo(f"  Run: {result.run_id}")
            if result.duration_seconds:
                click.echo(f"  Duration: {result.duration_seconds:.2f}s")
            if result.stage_durations:
                stage_summary = ", ".join(
                    f"{name}={duration:.2f}s"
                    for name, duration in result.stage_durations.items()
                )
                click.echo(f"  Stages: {stage_summary}")
            click.echo(f"  Cost: ${result.cost:.4f}")


@click.group()
def cli() -> None:
    pass


def add_language_option(func: _F) -> _F:
    return click.option(
        "--language",
        "-l",
        default="",
        help="Output report language (e.g. chinese, japanese).",
    )(func)


@cli.command()
@click.option("--source", default="github", help="Data source to fetch from.")
@click.option(
    "--config", "config_path", default="config.yaml", help="Path to config file."
)
@click.option("--dry-run", is_flag=True, help="Skip LLM calls and report writing.")
@click.option(
    "--limit", default=0, type=int, help="Max number of repos to analyze (0 = all)."
)
@click.option(
    "--no-rewrite",
    "skip_rewrite",
    is_flag=True,
    default=False,
    help="Skip the rewrite stage.",
)
@add_language_option
def run(
    source: str,
    config_path: str,
    dry_run: bool,
    limit: int,
    language: str,
    skip_rewrite: bool,
) -> None:
    setup_logging()
    run_cycle(
        source,
        config_path,
        limit,
        dry_run,
        language=language,
        skip_rewrite=skip_rewrite,
    )


@cli.command()
@click.option("--source", default="github", help="Data source to fetch from.")
@click.option(
    "--config", "config_path", default="config.yaml", help="Path to config file."
)
@click.option(
    "--limit", default=0, type=int, help="Max number of repos to analyze (0 = all)."
)
@click.option("--interval", default=3600, type=int, help="Seconds between runs.")
@click.option("--cycles", default=0, type=int, help="Max cycles (0 = infinite).")
@add_language_option
def schedule(
    source: str, config_path: str, limit: int, interval: int, cycles: int, language: str
) -> None:
    global _consecutive_failures
    setup_logging()
    load_config(config_path)

    def _signal_handler(signum: int, frame: object) -> None:
        _shutdown_event.set()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    cycle = 0
    while cycles == 0 or cycle < cycles:
        if _shutdown_event.is_set():
            click.echo("\nShutdown requested, stopping schedule.")
            break

        cycle += 1
        click.echo(f"\n--- Cycle {cycle} ---")

        try:
            run_cycle(source, config_path, limit, dry_run=False, language=language)
            _consecutive_failures = 0
        except Exception as exc:
            _consecutive_failures += 1
            get_logger().exception("Scheduled cycle %d failed: %s", cycle, exc)

        if cycles == 0 or cycle < cycles:
            if _shutdown_event.is_set():
                click.echo("\nShutdown requested, stopping schedule.")
                break
            backoff = (
                min(interval * (2**_consecutive_failures), _MAX_BACKOFF)
                if _consecutive_failures
                else interval
            )
            time.sleep(backoff)


@cli.command()
@click.option("--keyword", default=None, help="Search keyword.")
@click.option("--source", default=None, help="Filter by source.")
@click.option("--from", "date_from", default=None, help="Start date (YYYY-MM-DD).")
@click.option("--to", "date_to", default=None, help="End date (YYYY-MM-DD).")
@click.option("--limit", default=0, type=int, help="Max number of results (0 = all).")
@click.option(
    "--config", "config_path", default="config.yaml", help="Path to config file."
)
def search(
    keyword: str | None,
    source: str | None,
    date_from: str | None,
    date_to: str | None,
    limit: int,
    config_path: str,
) -> None:
    settings: Settings = load_config(config_path)
    kb_path = settings.knowledge_base.path

    results = search_reports(
        base_dir=kb_path,
        keyword=keyword,
        source=source,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )

    if not results:
        click.echo("No matching reports found.")
        return

    click.echo(f"Found {len(results)} report(s):")
    for filename, excerpt in results:
        click.echo(f"\n  {filename}")
        click.echo(f"    {excerpt}...")
