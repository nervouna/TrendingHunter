from datetime import datetime

from trending_hunter.models import Project, Report, Source, TokenUsage


def test_project_creation():
    p = Project(
        name="test/repo",
        source=Source.GITHUB,
        url="https://github.com/test/repo",
        stars=100,
        star_velocity=15.0,
        description="A test repo",
    )
    assert p.name == "test/repo"
    assert p.source == Source.GITHUB
    assert p.star_velocity == 15.0
    assert isinstance(p.fetched_at, datetime)


def test_project_defaults():
    p = Project(
        name="x/y",
        source=Source.GITHUB,
        url="https://github.com/x/y",
        stars=0,
        star_velocity=0.0,
        description="",
    )
    assert p.repo_age_days is None
    assert p.first_time_contributors is None
    assert p.readme_excerpt == ""


def test_token_usage_defaults():
    t = TokenUsage()
    assert t.input_tokens == 0
    assert t.output_tokens == 0


def test_token_usage_values():
    t = TokenUsage(input_tokens=100, output_tokens=200)
    assert t.input_tokens == 100
    assert t.output_tokens == 200


def test_report_creation():
    p = Project(
        name="x/y",
        source=Source.GITHUB,
        url="https://github.com/x/y",
        stars=50,
        star_velocity=5.0,
        description="test",
    )
    r = Report(
        project=p,
        draft_model="draft-m",
        audit_model="audit-m",
        rewrite_model="rewrite-m",
        sections={"TL;DR": "Test summary"},
        file_path="reports/2026-04-18-github-x-y.md",
    )
    assert r.token_usage["draft"] == TokenUsage()
    assert r.token_usage["audit"] == TokenUsage()
    assert r.token_usage["rewrite"] == TokenUsage()
    assert r.rewrite_model == "rewrite-m"
    assert r.sections["TL;DR"] == "Test summary"
    assert isinstance(r.generated_at, datetime)
