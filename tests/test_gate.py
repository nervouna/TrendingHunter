import pytest

from trending_hunter.gate import filter_projects
from trending_hunter.models import Project, Source
from trending_hunter.settings import SignalGateConfig


def _make_project(
    name: str, velocity: float, age_days: int | None = None, **kwargs: object
) -> Project:
    return Project(
        name=name,
        source=Source.GITHUB,
        url=f"https://github.com/{name}",
        stars=100,
        star_velocity=velocity,
        repo_age_days=age_days,
        description="test",
        **kwargs,
    )


DEFAULT_CONFIG = SignalGateConfig(
    min_star_velocity=10.0,
    max_repo_age_days=365,
    min_first_time_contributors=0,
)


@pytest.mark.parametrize(
    "velocity, age_days, expected",
    [
        (50.0, 100, True),
        (5.0, 100, False),
        (10.0, 100, True),
        (50.0, 400, False),
        (50.0, None, True),
    ],
)
def test_filter_velocity_and_age(velocity, age_days, expected):
    projects = [_make_project("a/b", velocity, age_days=age_days)]
    result = filter_projects(projects, DEFAULT_CONFIG)
    assert (len(result) == 1) == expected


def test_filter_empty():
    result = filter_projects([], DEFAULT_CONFIG)
    assert result == []


@pytest.mark.parametrize(
    "first_time_contributors, min_ftc, expected",
    [
        (5, 1, True),
        (0, 1, False),
        (None, 1, True),
    ],
)
def test_filter_first_time_contributors(first_time_contributors, min_ftc, expected):
    projects = [
        _make_project("a/b", 50.0, first_time_contributors=first_time_contributors)
    ]
    config = SignalGateConfig(
        min_star_velocity=10.0,
        max_repo_age_days=365,
        min_first_time_contributors=min_ftc,
    )
    result = filter_projects(projects, config)
    assert (len(result) == 1) == expected


# --- Per-source threshold tests ---


def _make_hn_project(name: str, velocity: float) -> Project:
    return Project(
        name=name,
        source=Source.HACKER_NEWS,
        url=f"https://example.com/{name}",
        stars=100,
        star_velocity=velocity,
        description="test",
    )


def _make_ph_project(name: str, velocity: float) -> Project:
    return Project(
        name=name,
        source=Source.PRODUCT_HUNT,
        url=f"https://producthunt.com/{name}",
        stars=100,
        star_velocity=velocity,
        description="test",
    )


def test_github_per_source_threshold():
    config = SignalGateConfig(min_star_velocity=10.0, github_min_star_velocity=5.0)
    projects = [
        _make_project("a/b", 7.0),  # above github-specific 5.0, below global 10.0
        _make_project("c/d", 3.0),  # below both
    ]
    result = filter_projects(projects, config, source=Source.GITHUB)
    names = [r.name for r in result]
    assert "a/b" in names
    assert "c/d" not in names


def test_hackernews_per_source_threshold():
    config = SignalGateConfig(min_star_velocity=10.0, hacker_news_min_star_velocity=3.0)
    projects = [
        _make_hn_project("story-a", 5.0),  # above hn-specific 3.0, below global 10.0
        _make_hn_project("story-b", 1.0),  # below both
    ]
    result = filter_projects(projects, config, source=Source.HACKER_NEWS)
    names = [r.name for r in result]
    assert "story-a" in names
    assert "story-b" not in names


def test_producthunt_per_source_threshold():
    config = SignalGateConfig(
        min_star_velocity=10.0, product_hunt_min_star_velocity=2.0
    )
    projects = [
        _make_ph_project("tool-a", 4.0),  # above ph-specific 2.0
        _make_ph_project("tool-b", 1.0),  # below both
    ]
    result = filter_projects(projects, config, source=Source.PRODUCT_HUNT)
    names = [r.name for r in result]
    assert "tool-a" in names
    assert "tool-b" not in names


def test_no_per_source_falls_back_to_global():
    config = SignalGateConfig(min_star_velocity=10.0)
    projects = [
        _make_project("a/b", 15.0),
        _make_project("c/d", 5.0),
    ]
    result = filter_projects(projects, config, source=Source.GITHUB)
    names = [r.name for r in result]
    assert "a/b" in names
    assert "c/d" not in names


def test_filter_projects_source_param_optional():
    config = SignalGateConfig(min_star_velocity=10.0)
    projects = [_make_project("a/b", 15.0)]
    result = filter_projects(projects, config)
    assert len(result) == 1
