from __future__ import annotations

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
