from __future__ import annotations

from unittest.mock import patch

from trending_hunter.fetchers.producthunt import _parse_ph_post, fetch_producthunt
from trending_hunter.models import Source


def _base_post() -> dict:
    return {
        "name": "AwesomeTool",
        "tagline": "Build better products faster",
        "url": "https://www.producthunt.com/posts/awesometool",
        "votesCount": 450,
        "createdAt": "2026-04-19T08:00:00Z",
        "commentsCount": 87,
    }


def test_parse_normal_post():
    project = _parse_ph_post(_base_post())
    assert project is not None
    assert project.name == "AwesomeTool"
    assert project.source == Source.PRODUCT_HUNT
    assert project.stars == 450
    assert project.star_velocity > 0
    assert project.description == "Build better products faster"


def test_parse_name_empty_returns_none():
    post = _base_post()
    post["name"] = ""
    assert _parse_ph_post(post) is None


def test_parse_name_missing_returns_none():
    post = _base_post()
    del post["name"]
    assert _parse_ph_post(post) is None


def test_parse_created_at_empty_uses_votes_as_velocity():
    post = _base_post()
    post["createdAt"] = ""
    post["votesCount"] = 100
    project = _parse_ph_post(post)
    assert project is not None
    assert project.star_velocity == 100.0


def test_parse_url_with_query_strips_params():
    post = _base_post()
    post["url"] = "https://www.producthunt.com/posts/awesometool?utm_source=foo&id=123"
    project = _parse_ph_post(post)
    assert project is not None
    assert project.url == "https://www.producthunt.com/posts/awesometool"
    assert "?" not in project.url


def test_parse_empty_node_returns_none():
    project = _parse_ph_post({})
    assert project is None


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_fetch_producthunt_flow(mock_gql):
    mock_gql.return_value = {
        "data": {
            "posts": {
                "edges": [
                    {"node": _base_post()},
                    {"node": {**_base_post(), "name": "SecondTool", "votesCount": 200}},
                ]
            }
        }
    }
    result = fetch_producthunt(token="fake", top_n=2)
    assert len(result) == 2
    assert result[0].name == "AwesomeTool"
    assert result[1].name == "SecondTool"
    mock_gql.assert_called_once()


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_fetch_producthunt_filters_empty_nodes(mock_gql):
    mock_gql.return_value = {
        "data": {
            "posts": {
                "edges": [
                    {"node": _base_post()},
                    {"node": {}},
                    {"node": {**_base_post(), "name": "Third"}},
                ]
            }
        }
    }
    result = fetch_producthunt(token="fake", top_n=3)
    assert len(result) == 2
    assert result[0].name == "AwesomeTool"
    assert result[1].name == "Third"


@patch("trending_hunter.fetchers.producthunt._ph_graphql")
def test_fetch_producthunt_empty_response(mock_gql):
    mock_gql.return_value = {"data": {}}
    result = fetch_producthunt(token="fake")
    assert result == []
