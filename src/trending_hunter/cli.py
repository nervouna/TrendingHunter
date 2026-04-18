from __future__ import annotations

import click

from trending_hunter.config import load_config
from trending_hunter.fetchers.github import fetch_trending


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--source", default="github", help="Data source to fetch from.")
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
def run(source: str, config_path: str) -> None:
    cfg = load_config(config_path)
    proxy = cfg.get("proxy")

    if source == "github":
        gh = cfg.get("sources", {}).get("github", {})
        language = gh.get("language", "")
        since = gh.get("since", "daily")
        repos = fetch_trending(language=language, since=since, proxy=proxy)
        click.echo(f"Fetched {len(repos)} trending repos:")
        for r in repos:
            vel = f"{r.star_velocity:.1f}" if r.star_velocity else "n/a"
            click.echo(f"  {r.name} | {r.stars} stars | {vel}/day | {r.description[:60]}")
    else:
        click.echo(f"Source '{source}' not yet implemented.")
