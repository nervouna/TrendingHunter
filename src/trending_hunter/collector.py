from __future__ import annotations

from datetime import datetime

import httpx

from trending_hunter.models import Project


def _tavily_extract(url: str, api_key: str) -> str:
    resp = httpx.post(
        "https://api.tavily.com/extract",
        json={"urls": [url], "extract_depth": "basic", "format": "markdown"},
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results", [])
    if results:
        return results[0].get("raw_content", "")[:3000]
    return ""


def enrich_projects(
    projects: list[Project],
    tavily_key: str | None = None,
) -> list[Project]:
    enriched: list[Project] = []
    for p in projects:
        readme = ""
        if tavily_key:
            try:
                readme = _tavily_extract(p.url, tavily_key)
            except httpx.HTTPError:
                pass

        updated = p.model_copy(
            update={"readme_excerpt": readme},
        )
        enriched.append(updated)
    return enriched
