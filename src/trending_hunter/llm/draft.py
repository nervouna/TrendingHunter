from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import DRAFT_SYSTEM, DRAFT_USER, get_language_modifier
from trending_hunter.llm.tools import tavily_extract, tavily_search
from trending_hunter.models import Project


def generate_draft(
    project: Project,
    client: LLMClient,
    tavily_key: str | None = None,
    language: str = "",
) -> tuple[dict[str, str], dict[str, int]]:
    extracted = ""
    search_ctx = ""

    if tavily_key:
        with ThreadPoolExecutor(max_workers=2) as executor:
            extract_future = executor.submit(tavily_extract, project.url, tavily_key)
            search_future = executor.submit(
                tavily_search,
                f"{project.name} open source review",
                tavily_key,
            )
            try:
                extracted = extract_future.result()
            except Exception:
                search_future.cancel()
                raise
            search_ctx = search_future.result()

    user = DRAFT_USER.format(
        name=project.name,
        url=project.url,
        stars=project.stars,
        star_velocity=project.star_velocity,
        repo_age_days=project.repo_age_days or "unknown",
        description=project.description,
        extracted_content=extracted or project.readme_excerpt or "N/A",
        search_context=search_ctx or "No search results available.",
        current_date=datetime.now().isoformat(),
    )
    system = DRAFT_SYSTEM + get_language_modifier(language)
    return client.call(system, user)
