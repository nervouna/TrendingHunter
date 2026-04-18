from __future__ import annotations

from trending_hunter.models import Project


def filter_projects(
    projects: list[Project],
    config: dict[str, object],
) -> list[Project]:
    min_velocity = float(config.get("min_star_velocity", 0))
    max_age = config.get("max_repo_age_days")
    max_age_int = int(max_age) if max_age is not None else None
    min_ftc = int(config.get("min_first_time_contributors", 0))

    result: list[Project] = []
    for p in projects:
        if p.star_velocity < min_velocity:
            continue
        if max_age_int is not None and p.repo_age_days is not None and p.repo_age_days > max_age_int:
            continue
        if min_ftc > 0 and p.first_time_contributors is not None and p.first_time_contributors < min_ftc:
            continue
        result.append(p)
    return result
