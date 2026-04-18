from __future__ import annotations

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import AUDIT_SYSTEM, AUDIT_USER
from trending_hunter.models import Project


def _sections_to_text(sections: dict[str, str]) -> str:
    parts: list[str] = []
    for name, content in sections.items():
        parts.append(f"## {name}\n{content}")
    return "\n\n".join(parts)


def audit_report(
    draft: dict[str, str],
    project: Project,
    client: LLMClient,
) -> tuple[dict[str, str], dict[str, int]]:
    user = AUDIT_USER.format(
        name=project.name,
        draft=_sections_to_text(draft),
        stars=project.stars,
        star_velocity=project.star_velocity,
        repo_age_days=project.repo_age_days or "unknown",
        description=project.description,
    )
    return client.call(AUDIT_SYSTEM, user)
