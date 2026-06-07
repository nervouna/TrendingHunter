from datetime import date
from pathlib import Path

import pytest
import yaml

from trending_hunter.cost import estimate_cost, format_cost_report
from trending_hunter.models import Project, Report, Source, TokenUsage
from trending_hunter.settings import ModelPricing
from trending_hunter.writer import (
    build_expected_filename,
    render_report,
    report_exists,
    save_report,
)


def _sample_report() -> Report:
    p = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=500,
        star_velocity=50.0,
        repo_age_days=30,
        description="A cool project",
    )
    return Report(
        project=p,
        draft_model="draft-m",
        audit_model="audit-m",
        rewrite_model="rewrite-m",
        token_usage={
            "draft": TokenUsage(input_tokens=100, output_tokens=200),
            "audit": TokenUsage(input_tokens=150, output_tokens=250),
        },
        sections={
            "TL;DR": "This is a cool project.",
            "What & Why": "Solves X problem.",
            "Why Now": "Because Y changed.",
            "Technology Wave": "Rides the Z trend.",
            "Supply & Demand": "Demand from A.",
            "Product Analysis": "For B users.",
            "Creativity & Differentiation": "Unique approach C.",
            "Competitive Landscape": "Competes with D.",
            "Community Signals": "Growing fast.",
            "Signal Assessment": "Real trend.",
            "Open Questions": "What about E?",
        },
        file_path="",
    )


def test_render_report_contains_all_sections():
    report = _sample_report()
    text = render_report(report)
    for name in report.sections:
        assert f"## {name}" in text


def test_render_report_has_metadata():
    report = _sample_report()
    text = render_report(report)
    assert "owner/repo" in text
    assert "github" in text
    assert "**Draft model**:" in text
    assert "**Audit model**:" in text
    assert "**Rewrite model**:" in text


@pytest.mark.parametrize(
    "source, name, url, stars, count_label, velocity_label, has_age, repo_age_days",
    [
        (
            Source.GITHUB,
            "owner/repo",
            "https://github.com/owner/repo",
            500,
            "Stars",
            "stars/day",
            True,
            30,
        ),
        (
            Source.HACKER_NEWS,
            "Some HN Story",
            "https://example.com/story",
            197,
            "Score",
            "score/day",
            False,
            None,
        ),
        (
            Source.PRODUCT_HUNT,
            "Cool Tool",
            "https://www.producthunt.com/posts/cool-tool",
            450,
            "Votes",
            "votes/day",
            False,
            None,
        ),
    ],
    ids=["github", "hackernews", "producthunt"],
)
def test_render_report_source_labels(
    source, name, url, stars, count_label, velocity_label, has_age, repo_age_days
):
    p = Project(
        name=name,
        source=source,
        url=url,
        stars=stars,
        star_velocity=100.0,
        repo_age_days=repo_age_days,
        description="A project",
    )
    report = Report(
        project=p,
        draft_model="m",
        audit_model="m",
        sections={"TL;DR": "test"},
        file_path="",
    )
    text = render_report(report)
    assert f"**{count_label}**: {stars}" in text
    assert velocity_label in text
    if has_age:
        assert "**Age**" in text
    else:
        assert "**Age**" not in text


def test_save_report_creates_file(tmp_path):
    report = _sample_report()
    path = save_report(report, str(tmp_path))
    assert path.exists()
    assert path.name.endswith(".md")
    content = path.read_text()
    assert "TL;DR" in content


def test_save_report_idempotent(tmp_path):
    report = _sample_report()
    path1 = save_report(report, str(tmp_path))
    path2 = save_report(report, str(tmp_path))
    assert path1 == path2
    assert path1.exists()


def test_estimate_cost_with_pricing():
    pricing = {"draft": ModelPricing(input_per_million=1.0, output_per_million=2.0)}
    cost = estimate_cost("draft", 1_000_000, 1_000_000, pricing)
    assert cost == 3.0


def test_estimate_cost_without_pricing():
    cost = estimate_cost("unknown-stage", 1000, 500)
    assert cost > 0


def test_format_cost_report():
    token_usage = {
        "draft": TokenUsage(input_tokens=100, output_tokens=200),
        "audit": TokenUsage(input_tokens=200, output_tokens=300),
    }
    text = format_cost_report(token_usage)
    assert "draft: 300 tokens" in text
    assert "audit: 500 tokens" in text
    assert "total: 800 tokens" in text


def test_build_expected_filename():
    p = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )
    result = build_expected_filename(p, "2026-04-19")
    assert result == "2026-04-19-github-owner-repo.md"


def test_report_exists_true(tmp_path):
    p = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )
    today = date(2026, 4, 19)
    filename = build_expected_filename(p, today.isoformat())
    (tmp_path / filename).write_text("placeholder")
    assert report_exists(p, str(tmp_path), today) is True


def test_report_exists_false(tmp_path):
    p = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )
    today = date(2026, 4, 19)
    assert report_exists(p, str(tmp_path), today) is False


def test_save_report_has_frontmatter(tmp_path):
    report = _sample_report()
    path = save_report(report, str(tmp_path))
    content = path.read_text()
    # Must start with YAML frontmatter delimiters
    assert content.startswith("---\n")
    # Extract frontmatter block
    parts = content.split("---\n", 2)
    assert len(parts) >= 3, "Expected frontmatter delimiters"
    fm = yaml.safe_load(parts[1])
    assert fm["status"] == "inbox"
    assert fm["source_type"] == "trending"
    assert fm["source"] == "https://github.com/owner/repo"
    assert fm["title"] == "owner/repo"
    assert fm["trending_source"] == "github"
    assert "trending" in fm["tags"]
    assert "created" in fm
    # Body should not start with H1 (render_report skips it)
    body = parts[2].strip()
    assert not body.startswith("# owner/repo")


def test_save_report_stdout(capsys):
    report = _sample_report()
    path = save_report(report, output="stdout")
    assert path == Path()
    captured = capsys.readouterr()
    assert "TL;DR" in captured.out
    assert "owner/repo" in captured.out
    assert "500" in captured.out


def test_save_report_default_is_file(tmp_path):
    report = _sample_report()
    path = save_report(report, base_dir=str(tmp_path))
    assert path.exists()
    assert path.name.endswith(".md")
