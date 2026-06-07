from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import (
    AUDIT_HN_HEADLINE_HINT,
    AUDIT_SYSTEM,
    AUDIT_USER,
    TAVILY_TOOLS,
    get_language_modifier,
)
from trending_hunter.llm.tools import tavily_extract, tavily_search
from trending_hunter.models import Project, Source
from trending_hunter.utils import sections_to_text


def _make_tool_handler(api_key: str) -> Callable[[str, dict[str, Any]], str]:
    def handler(name: str, input_data: dict[str, Any]) -> str:
        if name == "tavily_search":
            return tavily_search(input_data["query"], api_key)
        if name == "tavily_extract":
            return tavily_extract(input_data["url"], api_key)
        return f"Unknown tool: {name}"

    return handler


def audit_report(
    draft: dict[str, str],
    project: Project,
    client: LLMClient,
    tavily_key: str | None = None,
    language: str = "",
) -> tuple[dict[str, str], dict[str, int]]:
    user = AUDIT_USER.format(
        name=project.name,
        draft=sections_to_text(draft),
        stars=project.stars,
        star_velocity=project.star_velocity,
        repo_age_days=project.repo_age_days or "unknown",
        description=project.description,
        url=project.url,
        current_date=datetime.now().isoformat(),
    )

    system = AUDIT_SYSTEM
    if project.source == Source.HACKER_NEWS:
        system += AUDIT_HN_HEADLINE_HINT
    system += get_language_modifier(language)

    if tavily_key:
        handler = _make_tool_handler(tavily_key)
        return client.call_with_tools(system, user, TAVILY_TOOLS, handler)

    return client.call(system, user)
