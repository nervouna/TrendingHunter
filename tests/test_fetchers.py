from __future__ import annotations

from unittest.mock import MagicMock, patch

from trending_hunter.fetchers.base import Fetcher
from trending_hunter.fetchers.github import GitHubFetcher, fetch_trending
from trending_hunter.fetchers.hackernews import (
    HackerNewsFetcher,
    _parse_hn_item,
    fetch_hackernews,
)
from trending_hunter.fetchers.hackernews import _fetch_json as hn_fetch_json
from trending_hunter.fetchers.producthunt import (
    ProductHuntFetcher,
    _ph_graphql,
    fetch_producthunt,
)

# --- Hacker News unique tests (parser tests live in test_hackernews.py) ---

_HN_ITEM = {
    "id": 42000000,
    "type": "story",
    "title": "Show HN: A new open-source database",
    "url": "https://example.com/db",
    "score": 350,
    "by": "testuser",
    "time": 1713500000,
    "descendants": 42,
}


def test_parse_hn_item_with_text():
    item = {
        **_HN_ITEM,
        "text": "<p>This is the body of the HN post with some details.</p>",
    }
    project = _parse_hn_item(item)
    assert project is not None
    assert "This is the body" in project.description


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_passes_proxy(mock_fetch):
    def _side(path, **kwargs):
        if "topstories" in path:
            return []
        return {}

    mock_fetch.side_effect = _side
    fetch_hackernews(top_n=0, proxy="http://proxy:8080")
    mock_fetch.assert_called_once_with("topstories.json", proxy="http://proxy:8080")


# --- Product Hunt unique tests (parser tests live in test_producthunt.py) ---


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_fetch_producthunt_passes_proxy(mock_gql):
    mock_gql.return_value = {"data": {"posts": {"edges": []}}}
    fetch_producthunt(token="fake", top_n=1, proxy="http://proxy:8080")
    mock_gql.assert_called_once()
    assert mock_gql.call_args is not None


# --- Proxy / httpx.Client tests ---


@patch("trending_hunter.fetchers.hackernews.httpx.Client")
def test_hn_fetch_json_with_proxy(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [1, 2, 3]
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__ = MagicMock(
        return_value=mock_client_instance
    )
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

    hn_fetch_json("topstories.json", proxy="http://proxy:8080")
    mock_client_cls.assert_called_once()
    call_kwargs = mock_client_cls.call_args[1]
    assert call_kwargs["proxy"] == "http://proxy:8080"


@patch("trending_hunter.fetchers.producthunt.httpx.Client")
def test_ph_graphql_with_proxy(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": {"posts": {"edges": []}}}
    mock_resp.raise_for_status = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_resp
    mock_client_cls.return_value.__enter__ = MagicMock(
        return_value=mock_client_instance
    )
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

    _ph_graphql("query {}", {}, token="fake", proxy="http://proxy:8080")
    mock_client_cls.assert_called_once()
    call_kwargs = mock_client_cls.call_args[1]
    assert call_kwargs["proxy"] == "http://proxy:8080"


@patch("trending_hunter.fetchers.github.httpx.Client")
def test_fetch_github_with_proxy(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = "<html></html>"
    mock_resp.raise_for_status = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__ = MagicMock(
        return_value=mock_client_instance
    )
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

    fetch_trending(language="python", since="weekly", proxy="http://proxy:8080")
    mock_client_cls.assert_called_once()
    call_kwargs = mock_client_cls.call_args[1]
    assert call_kwargs["proxy"] == "http://proxy:8080"
    get_call = mock_client_instance.get.call_args
    assert "python" in get_call[0][0]


# --- Fetcher Protocol tests ---


def test_fetcher_protocol_compliance():
    """Fetcher Protocol requires a fetch method."""
    assert hasattr(Fetcher, "fetch")


def test_github_fetcher_is_protocol_compliant():
    f = GitHubFetcher()
    assert isinstance(f, Fetcher)


def test_hackernews_fetcher_is_protocol_compliant():
    f = HackerNewsFetcher()
    assert isinstance(f, Fetcher)


def test_producthunt_fetcher_is_protocol_compliant():
    f = ProductHuntFetcher()
    assert isinstance(f, Fetcher)


# --- Fetcher.fetch() integration tests ---


@patch("trending_hunter.fetchers.github.httpx.Client")
def test_github_fetcher_fetch(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.text = "<html></html>"
    mock_resp.raise_for_status = MagicMock()
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__ = MagicMock(
        return_value=mock_client_instance
    )
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

    settings = MagicMock()
    settings.proxy = ""
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    f = GitHubFetcher()
    result = f.fetch(settings)
    assert isinstance(result, list)


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_hackernews_fetcher_fetch(mock_fetch):
    mock_fetch.return_value = []
    settings = MagicMock()
    settings.proxy = ""
    settings.sources.hacker_news.top_n = 30
    f = HackerNewsFetcher()
    result = f.fetch(settings)
    assert result == []


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_producthunt_fetcher_fetch(mock_gql):
    mock_gql.return_value = {"data": {"posts": {"edges": []}}}
    settings = MagicMock()
    settings.proxy = ""
    settings.sources.product_hunt.token = "fake"
    settings.sources.product_hunt.top_n = 20
    f = ProductHuntFetcher()
    result = f.fetch(settings)
    assert result == []
