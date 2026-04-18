from __future__ import annotations

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import DRAFT_SYSTEM, DRAFT_USER
from trending_hunter.llm.tools import tavily_extract, tavily_search
from trending_hunter.models import Project


def generate_draft(
    project: Project,
    client: LLMClient,
    tavily_key: str | None = None,
) -> tuple[dict[str, str], dict[str, int]]:
    extracted = ""
    search_ctx = ""

    if tavily_key:
        extracted = tavily_extract(project.url, tavily_key)
        search_ctx = tavily_search(f"{project.name} open source review", tavily_key)

    user = DRAFT_USER.format(
        name=project.name,
        url=project.url,
        stars=project.stars,
        star_velocity=project.star_velocity,
        repo_age_days=project.repo_age_days or "unknown",
        description=project.description,
        extracted_content=extracted or project.readme_excerpt or "N/A",
        search_context=search_ctx or "No search results available.",
    )
    return client.call(DRAFT_SYSTEM, user)
