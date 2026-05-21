from __future__ import annotations

import threading
import time
from typing import Any, cast

import httpx

from trending_hunter.log import get_logger

log = get_logger()

_cache: dict[tuple[str, str], str] = {}

_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = httpx.Client()
    return _client


def clear_cache() -> None:
    _cache.clear()


_RETRYABLE = (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError)


def _retry_request(
    method: str,
    url: str,
    max_retries: int = 3,
    **kwargs: Any,
) -> httpx.Response:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = _get_client().request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                log.warning(
                    "Retry %d/%d after %ds: %s",
                    attempt + 1,
                    max_retries,
                    delay,
                    exc,
                )
                time.sleep(delay)
    if last_exc is None:
        raise RuntimeError("retry called with no attempts")
    raise last_exc


def tavily_search(query: str, api_key: str, max_results: int = 3) -> str:
    key = (f"search:{query}", api_key)
    if key in _cache:
        return _cache[key]

    log.info("Tavily search: %s", query)
    auth = f"Bearer {api_key}"
    resp = _retry_request(
        "POST",
        "https://api.tavily.com/search",
        json={
            "query": query,
            "max_results": max_results,
            "include_answer": False,
        },
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
        },
        timeout=15,
    )
    data = cast(dict[str, Any], resp.json())

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
    auth = f"Bearer {api_key}"
    resp = _retry_request(
        "POST",
        "https://api.tavily.com/extract",
        json={
            "urls": [url],
            "extract_depth": "basic",
            "format": "markdown",
        },
        headers={
            "Authorization": auth,
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    data = cast(dict[str, Any], resp.json())

    results = data.get("results", [])
    result = results[0].get("raw_content", "")[:max_chars] if results else ""
    _cache[key] = result
    return result
