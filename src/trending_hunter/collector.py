from __future__ import annotations

from datetime import datetime

import httpx

from trending_hunter.models import Project

_GITHUB_API = "https://api.github.com"


def _github_get(
    path: str,
    accept: str = "application/vnd.github+json",
    token: str | None = None,
) -> httpx.Response:
    headers: dict[str, str] = {"Accept": accept}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{_GITHUB_API}{path}"
    with httpx.Client(headers=headers, timeout=15) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp


def enrich_projects(
    projects: list[Project],
    token: str | None = None,
) -> list[Project]:
    enriched: list[Project] = []
    for p in projects:
        parts = p.name.split("/", 1)
        if len(parts) != 2:
            enriched.append(p)
            continue

        meta = _github_get(f"/repos/{parts[0]}/{parts[1]}", token=token).json()

        created_str = meta.get("created_at", "")
        if created_str:
            created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            age_days = (datetime.now(created.tzinfo) - created).days
        else:
            age_days = None

        try:
            readme = _github_get(
                f"/repos/{parts[0]}/{parts[1]}/readme",
                accept="application/vnd.github.raw",
                token=token,
            ).text[:2000]
        except httpx.HTTPError:
            readme = ""

        try:
            contributors = _github_get(
                f"/repos/{parts[0]}/{parts[1]}/contributors?per_page=100",
                token=token,
            ).json()
            first_time = sum(1 for c in contributors if c.get("contributions", 0) == 1)
        except httpx.HTTPError:
            first_time = None

        updated = p.model_copy(
            update={
                "stars": meta.get("stargazers_count", p.stars),
                "repo_age_days": age_days,
                "description": meta.get("description") or p.description,
                "readme_excerpt": readme,
                "first_time_contributors": first_time,
            }
        )
        enriched.append(updated)
    return enriched
