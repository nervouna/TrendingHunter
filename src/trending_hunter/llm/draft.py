from __future__ import annotations

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import DRAFT_SYSTEM, DRAFT_USER
from trending_hunter.models import Project


def generate_draft(
    project: Project,
    client: LLMClient,
) -> tuple[dict[str, str], dict[str, int]]:
    user = DRAFT_USER.format(
        name=project.name,
        url=project.url,
        stars=project.stars,
        star_velocity=project.star_velocity,
        repo_age_days=project.repo_age_days or "unknown",
        description=project.description,
        readme_excerpt=project.readme_excerpt or "N/A",
    )
    return client.call(DRAFT_SYSTEM, user)
