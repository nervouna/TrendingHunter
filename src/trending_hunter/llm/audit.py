from __future__ import annotations

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import AUDIT_SYSTEM, AUDIT_USER, TAVILY_TOOLS
from trending_hunter.llm.tools import tavily_extract, tavily_search
from trending_hunter.models import Project


def _sections_to_text(sections: dict[str, str]) -> str:
    parts: list[str] = []
    for name, content in sections.items():
        parts.append(f"## {name}\n{content}")
    return "\n\n".join(parts)


def _make_tool_handler(api_key: str):
    def handler(name: str, input_data: dict) -> str:
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
) -> tuple[dict[str, str], dict[str, int]]:
    user = AUDIT_USER.format(
        name=project.name,
        draft=_sections_to_text(draft),
        stars=project.stars,
        star_velocity=project.star_velocity,
        repo_age_days=project.repo_age_days or "unknown",
        description=project.description,
        url=project.url,
    )

    if tavily_key:
        handler = _make_tool_handler(tavily_key)
        return client.call_with_tools(AUDIT_SYSTEM, user, TAVILY_TOOLS, handler)

    return client.call(AUDIT_SYSTEM, user)
