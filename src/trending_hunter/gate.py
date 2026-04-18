from __future__ import annotations

from trending_hunter.models import Project
from trending_hunter.settings import SignalGateConfig


def filter_projects(
    projects: list[Project],
    config: SignalGateConfig,
) -> list[Project]:
    result: list[Project] = []
    for p in projects:
        if p.star_velocity < config.min_star_velocity:
            continue
        if p.repo_age_days is not None and p.repo_age_days > config.max_repo_age_days:
            continue
        if config.min_first_time_contributors > 0 and p.first_time_contributors is not None and p.first_time_contributors < config.min_first_time_contributors:
            continue
        result.append(p)
    return result
