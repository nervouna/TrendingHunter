from __future__ import annotations

import httpx

from trending_hunter.log import get_logger

log = get_logger()

_cache: dict[tuple[str, str], str] = {}


def _clear_cache() -> None:
    _cache.clear()


def tavily_search(query: str, api_key: str, max_results: int = 3) -> str:
    key = (f"search:{query}", api_key)
    if key in _cache:
        return _cache[key]

    log.info("Tavily search: %s", query)
    resp = httpx.post(
        "https://api.tavily.com/search",
        json={"query": query, "max_results": max_results, "include_answer": False},
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    parts: list[str] = []
    for r in data.get("results", []):
        title = r.get("title", "")
        content = r.get("content", "")
        url = r.get("url", "")
        parts.append(f"[{title}]({url})\n{content}")

    result = "\n\n".join(parts) if parts else "No results found."
    _cache[key] = result
    return result


def tavily_extract(url: str, api_key: str, max_chars: int = 3000) -> str:
    key = (f"extract:{url}", api_key)
    if key in _cache:
        return _cache[key]

    log.info("Tavily extract: %s", url)
    resp = httpx.post(
        "https://api.tavily.com/extract",
        json={"urls": [url], "extract_depth": "basic", "format": "markdown"},
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    results = data.get("results", [])
    result = results[0].get("raw_content", "")[:max_chars] if results else ""
    _cache[key] = result
    return result
