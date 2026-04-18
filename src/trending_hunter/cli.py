from __future__ import annotations

import click

from trending_hunter.collector import enrich_projects
from trending_hunter.config import load_config
from trending_hunter.fetchers.github import fetch_trending
from trending_hunter.gate import filter_projects
from trending_hunter.llm.audit import audit_report
from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.draft import generate_draft
from trending_hunter.models import Report


def _make_llm_client(api_key: str, stage_cfg: dict, default_model: str) -> LLMClient:
    return LLMClient(
        api_key=api_key,
        model=stage_cfg.get("model", default_model),
        max_tokens=stage_cfg.get("max_tokens", 4096),
    )


@click.group()
def cli() -> None:
    pass


@cli.command()
@click.option("--source", default="github", help="Data source to fetch from.")
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
@click.option("--dry-run", is_flag=True, help="Skip LLM calls and report writing.")
def run(source: str, config_path: str, dry_run: bool) -> None:
    cfg: dict[str, object] = load_config(config_path)
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

        if dry_run:
            for r in passed:
                vel = f"{r.star_velocity:.1f}" if r.star_velocity else "n/a"
                click.echo(f"  {r.name} | {r.stars} stars | {vel}/day")
            return

        enriched = enrich_projects(passed, token=token)

        llm_cfg = cfg.get("llm", {})
        api_key = llm_cfg.get("api_key", "")
        draft_cfg = llm_cfg.get("draft", {})
        audit_cfg = llm_cfg.get("audit", {})

        draft_client = _make_llm_client(api_key, draft_cfg, "claude-haiku-4-5-20251001")
        audit_client = _make_llm_client(api_key, audit_cfg, "claude-sonnet-4-5-20250514")

        for project in enriched:
            click.echo(f"\nAnalyzing {project.name}...")

            draft, draft_tokens = generate_draft(project, draft_client)
            click.echo(f"  Draft: {draft_tokens['input']}+{draft_tokens['output']} tokens")

            sections, audit_tokens = audit_report(draft, project, audit_client)
            click.echo(f"  Audit: {audit_tokens['input']}+{audit_tokens['output']} tokens")

            total_tokens = {
                "draft": draft_tokens["input"] + draft_tokens["output"],
                "audit": audit_tokens["input"] + audit_tokens["output"],
            }

            report = Report(
                project=project,
                draft_model=draft_cfg.get("model", ""),
                audit_model=audit_cfg.get("model", ""),
                token_usage=total_tokens,
                sections=sections,
                file_path="",
            )
            click.echo(f"  Generated {len(report.sections)} sections")

    else:
        click.echo(f"Source '{source}' not yet implemented.")
