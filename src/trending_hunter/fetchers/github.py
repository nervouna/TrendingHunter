from __future__ import annotations

import re

import httpx

from trending_hunter.models import Project, Source
from trending_hunter.settings import Settings

_TRENDING_URL = "https://github.com/trending"
_USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

_ARTICLE_RE = re.compile(r"<article[^>]*>(.*?)</article>", re.DOTALL)
_REPO_RE = re.compile(r'<h2[^>]*>\s*<a[^>]*href="/([^"]+)"')
_DESC_RE = re.compile(r"</h2>\s*<p[^>]*>(.*?)</p>", re.DOTALL)
_STARS_RE = re.compile(
    r'href="/[^/]+/[^/]+/stargazers"[^>]*>.*?</svg>\s*([\d,]+)', re.DOTALL
)
_VELOCITY_RE = re.compile(r"([\d,]+)\s*stars\s*(today|this week)")


def _parse_int(text: str) -> int:
    return int(text.replace(",", ""))


def parse_trending_html(html: str) -> list[Project]:
    repos: list[Project] = []
    for article in _ARTICLE_RE.finditer(html):
        body = article.group(1)

        m_repo = _REPO_RE.search(body)
        if not m_repo:
            continue
        repo_path = m_repo.group(1)

        m_desc = _DESC_RE.search(body)
        description = m_desc.group(1).strip() if m_desc else ""

        m_stars = _STARS_RE.search(body)
        stars = _parse_int(m_stars.group(1)) if m_stars else 0

        m_vel = _VELOCITY_RE.search(body)
        if m_vel:
            raw = _parse_int(m_vel.group(1))
            period = m_vel.group(2)
            velocity = float(raw) if period == "today" else raw / 7.0
        else:
            velocity = 0.0

        repos.append(
            Project(
                name=repo_path,
                source=Source.GITHUB,
                url=f"https://github.com/{repo_path}",
                stars=stars,
                star_velocity=velocity,
                description=description,
            )
        )
    return repos


def fetch_trending(
    language: str = "",
    since: str = "daily",
    proxy: str | None = None,
) -> list[Project]:
    url = _TRENDING_URL
    if language:
        url = f"{url}/{language}"
    params = {"since": since}

    headers = {"User-Agent": _USER_AGENT, "Accept": "text/html"}
    with httpx.Client(
        headers=headers,
        follow_redirects=True,
        timeout=15,
        proxy=proxy,
    ) as client:
        resp = client.get(url, params=params)
        resp.raise_for_status()

    return parse_trending_html(resp.text)


class GitHubFetcher:
    def fetch(self, settings: Settings) -> list[Project]:
        return fetch_trending(
            language=settings.sources.github.language,
            since=settings.sources.github.since,
            proxy=settings.proxy or None,
        )
