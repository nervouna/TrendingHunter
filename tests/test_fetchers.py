import pytest

from trending_hunter.fetchers.github import fetch_trending
from trending_hunter.fetchers.producthunt import fetch_producthunt
from trending_hunter.fetchers.hackernews import fetch_hackernews


def test_github_fetcher_exists():
    assert callable(fetch_trending)


def test_producthunt_fetcher_raises():
    with pytest.raises(NotImplementedError, match="Product Hunt"):
        fetch_producthunt()


def test_hackernews_fetcher_raises():
    with pytest.raises(NotImplementedError, match="Hacker News"):
        fetch_hackernews()
