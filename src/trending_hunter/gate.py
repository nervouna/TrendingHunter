from __future__ import annotations

from trending_hunter.models import Project, Source
from trending_hunter.settings import SignalGateConfig


def _resolve_min_velocity(config: SignalGateConfig, source: Source | None) -> float:
    if source == Source.GITHUB and config.github_min_star_velocity is not None:
        return config.github_min_star_velocity
    if (
        source == Source.HACKER_NEWS
        and config.hacker_news_min_star_velocity is not None
    ):
        return config.hacker_news_min_star_velocity
    if (
        source == Source.PRODUCT_HUNT
        and config.product_hunt_min_star_velocity is not None
    ):
        return config.product_hunt_min_star_velocity
    return config.min_star_velocity


def filter_projects(
    projects: list[Project],
    config: SignalGateConfig,
    source: Source | None = None,
) -> list[Project]:
    min_velocity = _resolve_min_velocity(config, source)
    result: list[Project] = []
    for p in projects:
        if p.star_velocity < min_velocity:
            continue
        if p.repo_age_days is not None and p.repo_age_days > config.max_repo_age_days:
            continue
        if (
            config.min_first_time_contributors > 0
            and p.first_time_contributors is not None
            and p.first_time_contributors < config.min_first_time_contributors
        ):
            continue
        result.append(p)
    return result
