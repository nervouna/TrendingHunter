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
from trending_hunter.writer import save_report
from trending_hunter.cost import estimate_cost


def _make_llm_client(stage_cfg: dict, default_model: str, timeout: float = 120.0) -> LLMClient:
    return LLMClient(
        api_key=stage_cfg.get("api_key", ""),
        model=stage_cfg.get("model", default_model),
        max_tokens=stage_cfg.get("max_tokens", 4096),
        base_url=stage_cfg.get("base_url") or None,
        timeout=timeout,
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
    cfg: dict[str, object] = load_config(config_path)
    proxy = cfg.get("proxy")

    if source == "github":
        gh = cfg.get("sources", {}).get("github", {})
        language = gh.get("language", "")
        since = gh.get("since", "daily")

        log.info("Fetching GitHub trending (language=%s, since=%s)", language, since)
        repos = fetch_trending(language=language, since=since, proxy=proxy)
        click.echo(f"Fetched {len(repos)} trending repos")

        gate_config = cfg.get("signal_gate", {})
        passed = filter_projects(repos, gate_config)
        click.echo(f"Passed signal gate: {len(passed)}/{len(repos)}")

        if limit > 0:
            passed = passed[:limit]
            click.echo(f"Limited to {len(passed)} repo(s)")

        if dry_run:
            for r in passed:
                vel = f"{r.star_velocity:.1f}" if r.star_velocity else "n/a"
                click.echo(f"  {r.name} | {r.stars} stars | {vel}/day")
            return

        tavily_key = cfg.get("tavily", {}).get("api_key") or None
        llm_cfg = cfg.get("llm", {})
        draft_cfg = llm_cfg.get("draft", {})
        audit_cfg = llm_cfg.get("audit", {})
        rewrite_cfg = llm_cfg.get("rewrite", {})

        draft_client = _make_llm_client(draft_cfg, "claude-haiku-4-5-20251001", timeout=120.0)
        audit_client = _make_llm_client(audit_cfg, "claude-sonnet-4-5-20250514", timeout=300.0)
        rewrite_client = _make_llm_client(rewrite_cfg, "claude-haiku-4-5-20251001", timeout=120.0)

        kb_path = cfg.get("knowledge_base", {}).get("path", "./reports")

        _clear_cache()

        for i, project in enumerate(passed):
            click.echo(f"\nAnalyzing {project.name} ({i+1}/{len(passed)})...")
            log.info("Processing project: %s", project.name)

            draft, draft_tokens = generate_draft(project, draft_client, tavily_key=tavily_key)
            click.echo(f"  Draft: {draft_tokens['input']}+{draft_tokens['output']} tokens")

            sections, audit_tokens = audit_report(draft, project, audit_client, tavily_key=tavily_key)
            click.echo(f"  Audit: {audit_tokens['input']}+{audit_tokens['output']} tokens")

            final, rewrite_tokens = rewrite_report(sections, project, rewrite_client)
            click.echo(f"  Rewrite: {rewrite_tokens['input']}+{rewrite_tokens['output']} tokens")

            total_tokens = {
                "draft": draft_tokens["input"] + draft_tokens["output"],
                "audit": audit_tokens["input"] + audit_tokens["output"],
                "rewrite": rewrite_tokens["input"] + rewrite_tokens["output"],
            }

            report = Report(
                project=project,
                draft_model=draft_cfg.get("model", ""),
                audit_model=audit_cfg.get("model", ""),
                token_usage=total_tokens,
                sections=final,
                file_path="",
            )

            path = save_report(report, base_dir=kb_path)
            click.echo(f"  Saved: {path}")

            cost = estimate_cost(draft_cfg.get("model", ""), draft_tokens["input"], draft_tokens["output"])
            cost += estimate_cost(audit_cfg.get("model", ""), audit_tokens["input"], audit_tokens["output"])
            cost += estimate_cost(rewrite_cfg.get("model", ""), rewrite_tokens["input"], rewrite_tokens["output"])
            click.echo(f"  Cost: ${cost:.4f}")

    else:
        click.echo(f"Source '{source}' not yet implemented.")


@cli.command()
@click.option("--keyword", default=None, help="Search keyword.")
@click.option("--source", default=None, help="Filter by source.")
@click.option("--config", "config_path", default="config.yaml", help="Path to config file.")
def search(keyword: str | None, source: str | None, config_path: str) -> None:
    cfg: dict[str, object] = load_config(config_path)
    kb_path = cfg.get("knowledge_base", {}).get("path", "./reports")

    results = search_reports(base_dir=str(kb_path), keyword=keyword, source=source)

    if not results:
        click.echo("No matching reports found.")
        return

    click.echo(f"Found {len(results)} report(s):")
    for filename, excerpt in results:
        click.echo(f"\n  {filename}")
        click.echo(f"    {excerpt}...")
