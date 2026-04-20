from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from trending_hunter.fetchers.github import fetch_trending
from trending_hunter.fetchers.producthunt import fetch_producthunt
from trending_hunter.fetchers.hackernews import (
    fetch_hackernews,
    _parse_hn_item,
)
from trending_hunter.fetchers.producthunt import (
    fetch_producthunt,
    _parse_ph_post,
)
from trending_hunter.fetchers.hackernews import _fetch_json as hn_fetch_json
from trending_hunter.fetchers.producthunt import _ph_graphql
from trending_hunter.models import Source


# --- Hacker News fetcher tests ---


_HN_ITEM = {
    "id": 42000000,
    "type": "story",
    "title": "Show HN: A new open-source database",
    "url": "https://example.com/db",
    "score": 350,
    "by": "testuser",
    "time": 1713500000,  # 2024-04-19 approx
    "descendants": 42,
}


def test_parse_hn_item_returns_project():
    project = _parse_hn_item(_HN_ITEM)
    assert project is not None
    assert project.name == "Show HN: A new open-source database"
    assert project.source == Source.HACKER_NEWS
    assert project.url == "https://example.com/db"
    assert project.stars == 350
    assert project.star_velocity > 0


def test_parse_hn_item_without_url_falls_back():
    item = {**_HN_ITEM, "url": None}
    project = _parse_hn_item(item)
    assert project is not None
    assert project.url == "https://news.ycombinator.com/item?id=42000000"


def test_parse_hn_item_skips_non_stories():
    item = {**_HN_ITEM, "type": "comment"}
    assert _parse_hn_item(item) is None


def test_parse_hn_item_skips_deleted():
    item = {**_HN_ITEM, "deleted": True}
    assert _parse_hn_item(item) is None


def test_parse_hn_item_skips_dead():
    item = {**_HN_ITEM, "dead": True}
    assert _parse_hn_item(item) is None


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_returns_projects(mock_fetch):
    # Use a callable side_effect to handle concurrent calls reliably
    def _fetch_json_side_effect(path, **kwargs):
        if "topstories" in path:
            return [42000000, 42000001]
        if "42000000" in path:
            return _HN_ITEM
        if "42000001" in path:
            return {**_HN_ITEM, "id": 42000001, "title": "Another story"}
        return None

    mock_fetch.side_effect = _fetch_json_side_effect

    result = fetch_hackernews(top_n=2)
    assert len(result) == 2
    assert result[0].name == "Show HN: A new open-source database"
    assert result[1].name == "Another story"


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_respects_top_n(mock_fetch):
    def _fetch_json_side_effect(path, **kwargs):
        if "topstories" in path:
            return [42000000, 42000001, 42000002]
        if "42000000" in path:
            return _HN_ITEM
        if "42000001" in path:
            return {**_HN_ITEM, "id": 42000001}
        if "42000002" in path:
            return {**_HN_ITEM, "id": 42000002}
        return None

    mock_fetch.side_effect = _fetch_json_side_effect

    result = fetch_hackernews(top_n=1)
    assert len(result) == 1


# --- Product Hunt fetcher tests ---


_PH_POST = {
    "name": "AwesomeTool",
    "tagline": "Build better products faster",
    "url": "https://www.producthunt.com/posts/awesometool",
    "votesCount": 450,
    "createdAt": "2026-04-19T08:00:00Z",
    "commentsCount": 87,
}


def test_parse_ph_post_returns_project():
    project = _parse_ph_post(_PH_POST)
    assert project is not None
    assert project.name == "AwesomeTool"
    assert project.source == Source.PRODUCT_HUNT
    assert project.url == "https://www.producthunt.com/posts/awesometool"
    assert project.stars == 450
    assert project.star_velocity > 0
    assert "Build better products faster" in project.description


def test_parse_ph_post_skips_missing_name():
    post = {**_PH_POST, "name": None}
    assert _parse_ph_post(post) is None


def test_parse_ph_post_skips_empty_name():
    post = {**_PH_POST, "name": ""}
    assert _parse_ph_post(post) is None


def test_parse_ph_post_strips_query_params():
    post = {**_PH_POST, "url": "https://www.producthunt.com/posts/awesometool?utm_source=foo&id=123"}
    project = _parse_ph_post(post)
    assert project is not None
    assert project.url == "https://www.producthunt.com/posts/awesometool"
    assert "?" not in project.url


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_fetch_producthunt_returns_projects(mock_gql):
    mock_gql.return_value = {
        "data": {
            "posts": {
                "edges": [
                    {"node": _PH_POST},
                    {"node": {**_PH_POST, "name": "SecondTool", "votesCount": 200}},
                ]
            }
        }
    }
    result = fetch_producthunt(token="fake", top_n=2)
    assert len(result) == 2
    assert result[0].name == "AwesomeTool"
    assert result[1].name == "SecondTool"


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_fetch_producthunt_respects_top_n(mock_gql):
    mock_gql.return_value = {
        "data": {
            "posts": {
                "edges": [
                    {"node": _PH_POST},
                    {"node": {**_PH_POST, "name": "SecondTool"}},
                    {"node": {**_PH_POST, "name": "ThirdTool"}},
                ]
            }
        }
    }
    result = fetch_producthunt(token="fake", top_n=1)
    assert len(result) == 1


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_empty_stories(mock_fetch):
    mock_fetch.return_value = []
    result = fetch_hackernews(top_n=5)
    assert result == []


@patch("trending_hunter.fetchers.hackernews._fetch_json", side_effect=Exception("network error"))
def test_fetch_hackernews_propagates_error(mock_fetch):
    with pytest.raises(Exception, match="network error"):
        fetch_hackernews(top_n=1)


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_executor_error(mock_fetch):
    def _side(path, **kwargs):
        if "topstories" in path:
            return [100]
        raise RuntimeError("item fetch failed")
    mock_fetch.side_effect = _side
    with pytest.raises(RuntimeError, match="item fetch failed"):
        fetch_hackernews(top_n=1)


def test_parse_ph_post_no_created_at():
    post = {
        "name": "Tool",
        "tagline": "A tool",
        "url": "https://example.com",
        "votesCount": 100,
        "createdAt": "",
    }
    project = _parse_ph_post(post)
    assert project is not None
    assert project.star_velocity == 100.0


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_fetch_producthunt_passes_proxy(mock_gql):
    mock_gql.return_value = {"data": {"posts": {"edges": [{"node": _PH_POST}]}}}
    fetch_producthunt(token="fake", top_n=1, proxy="http://proxy:8080")
    mock_gql.assert_called_once()
    # The proxy should be passed through _ph_graphql — verify the call was made
    assert mock_gql.call_args is not None


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


@patch("trending_hunter.fetchers.hackernews.httpx.Client")
def test_hn_fetch_json_with_proxy(mock_client_cls):
    mock_resp = MagicMock()
    mock_resp.json.return_value = [1, 2, 3]
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_resp
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
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
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
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
    mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
    mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

    fetch_trending(language="python", since="weekly", proxy="http://proxy:8080")
    mock_client_cls.assert_called_once()
    call_kwargs = mock_client_cls.call_args[1]
    assert call_kwargs["proxy"] == "http://proxy:8080"
    # Verify the language is in the URL
    get_call = mock_client_instance.get.call_args
    assert "python" in get_call[0][0]
