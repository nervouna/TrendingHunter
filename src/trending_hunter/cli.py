from __future__ import annotations

import click


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--source", default="github", help="Data source to fetch from.")
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
def run(source: str, config_path: str) -> None:
    pass
