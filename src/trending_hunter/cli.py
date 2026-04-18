from __future__ import annotations

import click

from trending_hunter.config import load_config
from trending_hunter.fetchers.github import fetch_trending
from trending_hunter.gate import filter_projects
from trending_hunter.llm.audit import audit_report
from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.draft import generate_draft
from trending_hunter.llm.rewrite import rewrite_report
from trending_hunter.llm.tools import _clear_cache
from trending_hunter.log import get_logger, setup_logging
from trending_hunter.models import Report
from trending_hunter.search import search_reports
from trending_hunter.settings import LLMStageConfig, Settings
from trending_hunter.writer import save_report
from trending_hunter.cost import estimate_cost


def _make_llm_client(stage_cfg: LLMStageConfig) -> LLMClient:
    return LLMClient(
        api_key=stage_cfg.api_key,
        model=stage_cfg.model,
        max_tokens=stage_cfg.max_tokens,
        base_url=stage_cfg.base_url or None,
        timeout=stage_cfg.timeout,
    )


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

        tavily_key = settings.tavily.api_key or None

        draft_client = _make_llm_client(settings.llm.draft)
        audit_client = _make_llm_client(settings.llm.audit)
        rewrite_client = _make_llm_client(settings.llm.rewrite)

        kb_path = settings.knowledge_base.path

        _clear_cache()

        for i, project in enumerate(passed):
            click.echo(f"\nAnalyzing {project.name} ({i+1}/{len(passed)})...")
            log.info("Processing project: %s", project.name)

            draft, draft_tokens = generate_draft(project, draft_client, tavily_key=tavily_key)
            click.echo(f"  Draft: {draft_tokens['input']}+{draft_tokens['output']} tokens")

            sections, audit_tokens = audit_report(draft, project, audit_client, tavily_key=tavily_key)
            click.echo(f"  Audit: {audit_tokens['input']}+{audit_tokens['output']} tokens")

            sections, rewrite_tokens = rewrite_report(sections, rewrite_client)
            click.echo(f"  Rewrite: {rewrite_tokens['input']}+{rewrite_tokens['output']} tokens")

            total_tokens = {
                "draft": draft_tokens["input"] + draft_tokens["output"],
                "audit": audit_tokens["input"] + audit_tokens["output"],
                "rewrite": rewrite_tokens["input"] + rewrite_tokens["output"],
            }

            report = Report(
                project=project,
                draft_model=settings.llm.draft.model,
                audit_model=settings.llm.audit.model,
                token_usage=total_tokens,
                sections=sections,
                file_path="",
            )

            path = save_report(report, base_dir=kb_path)
            click.echo(f"  Saved: {path}")

            cost = estimate_cost(settings.llm.draft.model, draft_tokens["input"], draft_tokens["output"])
            cost += estimate_cost(settings.llm.audit.model, audit_tokens["input"], audit_tokens["output"])
            cost += estimate_cost(settings.llm.rewrite.model, rewrite_tokens["input"], rewrite_tokens["output"])
            click.echo(f"  Cost: ${cost:.4f}")

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
