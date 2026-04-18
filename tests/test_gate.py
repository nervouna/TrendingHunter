from datetime import datetime, timedelta

from trending_hunter.models import Project, Source
from trending_hunter.gate import filter_projects
from trending_hunter.collector import enrich_projects


def _make_project(name: str, velocity: float, age_days: int | None = None, **kwargs: object) -> Project:
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


DEFAULT_CONFIG = {
    "min_star_velocity": 10.0,
    "max_repo_age_days": 365,
    "min_first_time_contributors": 0,
}


def test_filter_by_velocity():
    projects = [
        _make_project("a/b", 50.0),
        _make_project("c/d", 5.0),
        _make_project("e/f", 10.0),
    ]
    result = filter_projects(projects, DEFAULT_CONFIG)
    names = [r.name for r in result]
    assert "a/b" in names
    assert "e/f" in names
    assert "c/d" not in names


def test_filter_by_age():
    projects = [
        _make_project("a/b", 50.0, age_days=100),
        _make_project("c/d", 50.0, age_days=400),
    ]
    result = filter_projects(projects, DEFAULT_CONFIG)
    assert len(result) == 1
    assert result[0].name == "a/b"


def test_filter_keeps_unknown_age():
    projects = [_make_project("a/b", 50.0, age_days=None)]
    result = filter_projects(projects, DEFAULT_CONFIG)
    assert len(result) == 1


def test_filter_empty():
    result = filter_projects([], DEFAULT_CONFIG)
    assert result == []


def test_enrich_adds_readme(enrich_stub):
    projects = [_make_project("a/b", 50.0)]
    enriched = enrich_projects(projects, tavily_key="fake")
    assert len(enriched) == 1
    assert enriched[0].readme_excerpt == "# Test Repo\nThis is a test README."


def test_filter_by_first_time_contributors():
    projects = [
        _make_project("a/b", 50.0, first_time_contributors=5),
        _make_project("c/d", 50.0, first_time_contributors=0),
        _make_project("e/f", 50.0, first_time_contributors=None),
    ]
    config = {**DEFAULT_CONFIG, "min_first_time_contributors": 1}
    result = filter_projects(projects, config)
    names = [r.name for r in result]
    assert "a/b" in names
    assert "c/d" not in names
    assert "e/f" in names
