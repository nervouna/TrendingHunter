from datetime import datetime, timezone

import pytest

from trending_hunter.utils import daily_velocity, normalize_url, sections_to_text


@pytest.mark.parametrize(
    "input_url, expected",
    [
        ("https://github.com/owner/repo", "https://github.com/owner/repo"),
        ("https://github.com/owner/repo/", "https://github.com/owner/repo"),
        (
            "https://www.producthunt.com/posts/cool-tool",
            "https://producthunt.com/posts/cool-tool",
        ),
        (
            "https://www.producthunt.com/posts/cool-tool?ref=home",
            "https://producthunt.com/posts/cool-tool",
        ),
        (
            "https://news.ycombinator.com/item?id=12345",
            "https://news.ycombinator.com/item?id=12345",
        ),
        ("https://example.com/blog/post", "https://example.com/blog/post"),
        ("https://www.example.com/path", "https://example.com/path"),
        ("https://GitHub.com/owner/repo", "https://github.com/owner/repo"),
        ("https://example.com/page#section", "https://example.com/page"),
        ("", ""),
    ],
    ids=[
        "github-basic",
        "github-trailing-slash",
        "producthunt-removes-www",
        "producthunt-removes-query",
        "hn-item-keeps-query",
        "external-link",
        "removes-www",
        "lowercase-host",
        "removes-fragment",
        "empty-url",
    ],
)
def test_normalize_url(input_url, expected):
    assert normalize_url(input_url) == expected


def test_cross_source_same_github_project():
    gh_url = "https://github.com/owner/repo"
    hn_url = "https://www.github.com/owner/repo/?ref=hackernews"
    assert normalize_url(gh_url) == normalize_url(hn_url)


# --- sections_to_text ---


def test_sections_to_text():
    sections = {"TL;DR": "Summary.", "What & Why": "Details."}
    text = sections_to_text(sections)
    assert "## TL;DR" in text
    assert "## What & Why" in text
    assert "Summary." in text


def test_sections_to_text_empty():
    assert sections_to_text({}) == ""


# --- daily_velocity ---


def test_daily_velocity_basic():
    now = datetime(2026, 4, 20, 12, 0, 0, tzinfo=timezone.utc)
    posted = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
    # 100 score in 24h = 100/day
    assert daily_velocity(100, posted, now=now) == pytest.approx(100.0)


def test_daily_velocity_half_day():
    now = datetime(2026, 4, 20, 0, 0, 0, tzinfo=timezone.utc)
    posted = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
    # 100 score in 12h = 200/day
    assert daily_velocity(100, posted, now=now) == pytest.approx(200.0)


def test_daily_velocity_minimum_one_hour():
    now = datetime(2026, 4, 19, 12, 5, 0, tzinfo=timezone.utc)
    posted = datetime(2026, 4, 19, 12, 0, 0, tzinfo=timezone.utc)
    # 5 minutes ago, clamped to 1 hour
    result = daily_velocity(100, posted, now=now)
    assert result == pytest.approx(100.0 / 1 * 24)


# --- Re-export backward compatibility ---


def test_writer_sections_to_text_reexport():
    from trending_hunter.utils import sections_to_text as utils_fn
    from trending_hunter.writer import sections_to_text as writer_fn

    assert writer_fn is utils_fn


def test_fetchers_daily_velocity_reexport():
    from trending_hunter.fetchers import daily_velocity as fetchers_fn
    from trending_hunter.utils import daily_velocity as utils_fn

    assert fetchers_fn is utils_fn
