from __future__ import annotations

import time
from unittest.mock import patch

from trending_hunter.fetchers.hackernews import _parse_hn_item, fetch_hackernews
from trending_hunter.models import Source


def _base_item() -> dict:
    return {
        "id": 42000000,
        "type": "story",
        "title": "Show HN: A new open-source database",
        "url": "https://example.com/db",
        "score": 350,
        "by": "testuser",
        "time": int(time.time()) - 3600,
        "descendants": 42,
    }


def test_parse_normal_story():
    project = _parse_hn_item(_base_item())
    assert project is not None
    assert project.name == "Show HN: A new open-source database"
    assert project.source == Source.HACKER_NEWS
    assert project.url == "https://example.com/db"
    assert project.stars == 350
    assert project.star_velocity > 0


def test_parse_non_story_returns_none():
    item = _base_item()
    item["type"] = "comment"
    assert _parse_hn_item(item) is None


def test_parse_deleted_returns_none():
    item = _base_item()
    item["deleted"] = True
    assert _parse_hn_item(item) is None


def test_parse_dead_returns_none():
    item = _base_item()
    item["dead"] = True
    assert _parse_hn_item(item) is None


def test_parse_no_url_falls_back_to_hn_item_url():
    item = _base_item()
    item["url"] = None
    project = _parse_hn_item(item)
    assert project is not None
    assert project.url == f"https://news.ycombinator.com/item?id={item['id']}"


def test_parse_text_field_concatenated():
    item = _base_item()
    item["text"] = "<p>Details about the project.</p>"
    project = _parse_hn_item(item)
    assert project is not None
    assert "Details about the project" in project.description
    assert "Show HN" in project.description
    assert " — " in project.description


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_flow(mock_fetch):
    def _side(path, **kwargs):
        if "topstories" in path:
            return [42000000, 42000001]
        if "42000000" in path:
            return _base_item()
        if "42000001" in path:
            return {**_base_item(), "id": 42000001, "title": "Another story"}
        return None

    mock_fetch.side_effect = _side
    result = fetch_hackernews(top_n=2)
    assert len(result) == 2
    assert result[0].name == "Show HN: A new open-source database"
    assert result[1].name == "Another story"


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_empty(mock_fetch):
    mock_fetch.return_value = []
    result = fetch_hackernews(top_n=5)
    assert result == []


@patch("trending_hunter.fetchers.hackernews._fetch_json")
def test_fetch_hackernews_skips_deleted_items(mock_fetch):
    def _side(path, **kwargs):
        if "topstories" in path:
            return [100, 200]
        if "100" in path:
            return {**_base_item(), "id": 100}
        if "200" in path:
            return {**_base_item(), "id": 200, "deleted": True}
        return None

    mock_fetch.side_effect = _side
    result = fetch_hackernews(top_n=2)
    assert len(result) == 1
    assert result[0].name == "Show HN: A new open-source database"
