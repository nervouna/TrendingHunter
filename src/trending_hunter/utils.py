from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    parsed = urlparse(url)

    scheme = parsed.scheme.lower()
    host = parsed.hostname or ""
    host = host.lower().removeprefix("www.")

    path = parsed.path.rstrip("/")

    # Hacker News item URLs: keep ?id= as part of the identity
    is_hn_item = host == "news.ycombinator.com" and path == "/item"
    query = parsed.query if is_hn_item else ""

    return urlunparse((scheme, host, path, "", query, ""))


def daily_velocity(
    score: int, posted_at: datetime, now: datetime | None = None
) -> float:
    now = now or datetime.now(timezone.utc)
    hours = max((now - posted_at).total_seconds() / 3600, 1)
    return score / hours * 24


def sections_to_text(sections: dict[str, str]) -> str:
    parts: list[str] = []
    for name, content in sections.items():
        parts.append(f"## {name}\n{content}")
    return "\n\n".join(parts)
