from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from trending_hunter.cost import estimate_cost
from trending_hunter.dedup import SeenUrls
from trending_hunter.llm.audit import audit_report
from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.draft import generate_draft
from trending_hunter.llm.rewrite import rewrite_report
from trending_hunter.llm.tools import clear_cache
from trending_hunter.log import get_logger
from trending_hunter.models import Project, Report, TokenUsage
from trending_hunter.settings import Settings
from trending_hunter.writer import get_report_path, save_report

log = get_logger()


@dataclass
class PipelineResult:
    project: Project
    token_usage: dict[str, TokenUsage] = field(default_factory=dict)
    stage_durations: dict[str, float] = field(default_factory=dict)
    file_path: str = ""
    cost: float = 0.0
    duration_seconds: float = 0.0
    run_id: str = ""
    status: str = "success"
    error: str | None = None


def run_pipeline(
    projects: list[Project],
    settings: Settings,
    language: str = "",
    seen: SeenUrls | None = None,
    skip_rewrite: bool = False,
) -> list[PipelineResult]:
    clear_cache()
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
    run_id = uuid.uuid4().hex[:8]

    results: list[PipelineResult] = []
    log.info("Pipeline run %s started: projects=%d", run_id, len(projects))

    try:
        for project in projects:
            project_started = time.perf_counter()
            dedup_url = project.normalized_url or project.url
            if seen and seen.is_seen(dedup_url):
                path = get_report_path(project, kb_path)
                duration = time.perf_counter() - project_started
                log.info(
                    "Pipeline run %s skipped %s: already processed url=%s",
                    run_id,
                    project.name,
                    dedup_url,
                )
                results.append(
                    PipelineResult(
                        project=project,
                        file_path=str(path) if path.exists() else "",
                        duration_seconds=duration,
                        run_id=run_id,
                        status="skipped",
                    )
                )
                continue

            try:
                log.info("Pipeline run %s processing %s", run_id, project.name)
                stage_durations: dict[str, float] = {}

                stage_started = time.perf_counter()
                draft, draft_tokens = generate_draft(
                    project,
                    draft_client,
                    tavily_key=tavily_key,
                    language=language,
                )
                stage_durations["draft"] = time.perf_counter() - stage_started

                stage_started = time.perf_counter()
                sections, audit_tokens = audit_report(
                    draft,
                    project,
                    audit_client,
                    tavily_key=tavily_key,
                    language=language,
                )
                stage_durations["audit"] = time.perf_counter() - stage_started

                rewrite_tokens: dict[str, int] = {"input": 0, "output": 0}
                if not skip_rewrite:
                    stage_started = time.perf_counter()
                    sections, rewrite_tokens = rewrite_report(
                        sections,
                        rewrite_client,
                        language=language,
                    )
                    stage_durations["rewrite"] = time.perf_counter() - stage_started
                else:
                    stage_durations["rewrite"] = 0.0

                token_usage = {
                    "draft": TokenUsage(
                        input_tokens=draft_tokens["input"],
                        output_tokens=draft_tokens["output"],
                    ),
                    "audit": TokenUsage(
                        input_tokens=audit_tokens["input"],
                        output_tokens=audit_tokens["output"],
                    ),
                    "rewrite": TokenUsage(
                        input_tokens=rewrite_tokens["input"],
                        output_tokens=rewrite_tokens["output"],
                    ),
                }

                report = Report(
                    project=project,
                    draft_model=settings.llm.draft.model,
                    audit_model=settings.llm.audit.model,
                    rewrite_model="" if skip_rewrite else settings.llm.rewrite.model,
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
                duration = time.perf_counter() - project_started

                log.info(
                    "Pipeline run %s completed %s: duration=%.2fs cost=%.4f",
                    run_id,
                    project.name,
                    duration,
                    cost,
                )
                results.append(
                    PipelineResult(
                        project=project,
                        token_usage=token_usage,
                        stage_durations=stage_durations,
                        file_path=str(path),
                        cost=cost,
                        duration_seconds=duration,
                        run_id=run_id,
                    )
                )

                if seen:
                    seen.mark_seen(dedup_url)

            except Exception as exc:
                duration = time.perf_counter() - project_started
                log.exception(
                    "Pipeline run %s failed %s after %.2fs",
                    run_id,
                    project.name,
                    duration,
                )
                results.append(
                    PipelineResult(
                        project=project,
                        error=str(exc),
                        duration_seconds=duration,
                        run_id=run_id,
                        status="error",
                    )
                )
    finally:
        if seen:
            seen.save()
        log.info("Pipeline run %s finished", run_id)

    return results
