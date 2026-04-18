from __future__ import annotations

import click

from trending_hunter.collector import enrich_projects
from trending_hunter.config import load_config
from trending_hunter.fetchers.github import fetch_trending
from trending_hunter.gate import filter_projects


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
        click.echo(f"Fetched {len(repos)} trending repos")

        gate_config = cfg.get("signal_gate", {})
        passed = filter_projects(repos, gate_config)
        click.echo(f"Passed signal gate: {len(passed)}/{len(repos)}")

        token = cfg.get("github_token")
        enriched = enrich_projects(passed, token=token)

        for r in enriched:
            vel = f"{r.star_velocity:.1f}" if r.star_velocity else "n/a"
            age = f"{r.repo_age_days}d" if r.repo_age_days is not None else "?"
            click.echo(f"  {r.name} | {r.stars} stars | {vel}/day | age: {age} | {r.description[:50]}")
    else:
        click.echo(f"Source '{source}' not yet implemented.")
