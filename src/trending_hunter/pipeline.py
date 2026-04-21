from __future__ import annotations

from dataclasses import dataclass, field

from trending_hunter.cost import estimate_cost
from trending_hunter.dedup import SeenUrls
from trending_hunter.llm.audit import audit_report
from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.draft import generate_draft
from trending_hunter.llm.rewrite import rewrite_report
from trending_hunter.log import get_logger
from trending_hunter.models import Project, Report, TokenUsage
from trending_hunter.settings import Settings
from trending_hunter.writer import get_report_path, save_report

log = get_logger()


@dataclass
class PipelineResult:
    project: Project
    token_usage: dict[str, TokenUsage] = field(default_factory=dict)
    file_path: str = ""
    cost: float = 0.0
    status: str = "success"
    error: str | None = None


def run_pipeline(projects: list[Project], settings: Settings, language: str = "", seen: SeenUrls | None = None) -> list[PipelineResult]:
    tavily_key = settings.tavily.api_key or None
    draft_client = LLMClient(
        api_key=settings.llm.draft.api_key,
        model=settings.llm.draft.model,
        max_tokens=settings.llm.draft.max_tokens,
        base_url=settings.llm.draft.base_url or None,
        timeout=settings.llm.draft.timeout,
    )
    audit_client = LLMClient(
        api_key=settings.llm.audit.api_key,
        model=settings.llm.audit.model,
        max_tokens=settings.llm.audit.max_tokens,
        base_url=settings.llm.audit.base_url or None,
        timeout=settings.llm.audit.timeout,
    )
    rewrite_client = LLMClient(
        api_key=settings.llm.rewrite.api_key,
        model=settings.llm.rewrite.model,
        max_tokens=settings.llm.rewrite.max_tokens,
        base_url=settings.llm.rewrite.base_url or None,
        timeout=settings.llm.rewrite.timeout,
    )
    kb_path = settings.knowledge_base.path
    pricing = settings.model_pricing or None

    results: list[PipelineResult] = []

    for project in projects:
        dedup_url = project.normalized_url or project.url
        if seen and seen.is_seen(dedup_url):
            log.info("Skipping %s — already processed (url=%s)", project.name, dedup_url)
            results.append(PipelineResult(project=project, status="skipped"))
            continue

        try:
            draft, draft_tokens = generate_draft(project, draft_client, tavily_key=tavily_key, language=language)
            sections, audit_tokens = audit_report(draft, project, audit_client, tavily_key=tavily_key, language=language)
            sections, rewrite_tokens = rewrite_report(sections, rewrite_client, language=language)

            token_usage = {
                "draft": TokenUsage(input_tokens=draft_tokens["input"], output_tokens=draft_tokens["output"]),
                "audit": TokenUsage(input_tokens=audit_tokens["input"], output_tokens=audit_tokens["output"]),
                "rewrite": TokenUsage(input_tokens=rewrite_tokens["input"], output_tokens=rewrite_tokens["output"]),
            }

            report = Report(
                project=project,
                draft_model=settings.llm.draft.model,
                audit_model=settings.llm.audit.model,
                rewrite_model=settings.llm.rewrite.model,
                token_usage=token_usage,
                sections=sections,
                file_path="",
            )

            path = save_report(report, base_dir=kb_path)

            cost = sum(
                estimate_cost(model, t.input_tokens, t.output_tokens, pricing)
                for model, t in (
                    (settings.llm.draft.model, token_usage["draft"]),
                    (settings.llm.audit.model, token_usage["audit"]),
                    (settings.llm.rewrite.model, token_usage["rewrite"]),
                )
            )

            results.append(PipelineResult(
                project=project,
                token_usage=token_usage,
                file_path=str(path),
                cost=cost,
            ))

            if seen:
                seen.mark_seen(dedup_url)

        except Exception as exc:
            log.error("Failed to process %s: %s", project.name, exc)
            results.append(PipelineResult(project=project, error=str(exc), status="error"))

    if seen:
        seen.save()

    return results
