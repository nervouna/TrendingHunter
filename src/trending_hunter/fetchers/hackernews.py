from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone

import httpx

from trending_hunter.models import Project, Source

_HN_API = "https://hacker-news.firebaseio.com/v0"
_USER_AGENT = "TrendingHunter/0.1"


def _fetch_json(path: str, proxy: str | None = None) -> object:
    client_kwargs: dict[str, object] = {
        "headers": {"User-Agent": _USER_AGENT},
        "timeout": 15,
    }
    if proxy:
        client_kwargs["proxy"] = proxy
    with httpx.Client(**client_kwargs) as client:
        resp = client.get(f"{_HN_API}/{path}")
        resp.raise_for_status()
    return resp.json()


def _parse_hn_item(item: dict) -> Project | None:
    if item.get("type") != "story":
        return None
    if item.get("deleted") or item.get("dead"):
        return None

    story_id = item["id"]
    title = item.get("title", "")
    url = item.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
    score = item.get("score", 0)
    ts = item.get("time", 0)

    post_time = datetime.fromtimestamp(ts, tz=timezone.utc)
    now = datetime.now(timezone.utc)
    hours = max((now - post_time).total_seconds() / 3600, 1)
    velocity = score / hours * 24

    text = item.get("text", "")
    description = title
    if text:
        description = f"{title} — {text[:200]}"

    return Project(
        name=title,
        source=Source.HACKER_NEWS,
        url=url,
        stars=score,
        star_velocity=round(velocity, 2),
        repo_age_days=0,
        description=description,
    )


def fetch_hackernews(
    top_n: int = 30,
    proxy: str | None = None,
) -> list[Project]:
    story_ids: list[int] = _fetch_json("topstories.json", proxy=proxy)  # type: ignore[assignment]
    story_ids = story_ids[:top_n]

    projects: list[Project] = []
    if not story_ids:
        return projects

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        def _fetch_item(story_id: int) -> object:
            return _fetch_json(f"item/{story_id}.json", proxy=proxy)

        try:
            items = list(executor.map(_fetch_item, story_ids))
        except Exception:
            raise

    for item in items:
        project = _parse_hn_item(item)
        if project is not None:
            projects.append(project)

    return projects
