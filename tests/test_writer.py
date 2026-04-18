from datetime import date

from trending_hunter.models import Project, Report, Source, TokenUsage
from trending_hunter.writer import (
    build_expected_filename,
    render_report,
    report_exists,
    save_report,
    sections_to_text,
)
from trending_hunter.cost import estimate_cost, format_cost_report
from trending_hunter.settings import ModelPricing


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


def test_render_report_github_labels():
    report = _sample_report()
    text = render_report(report)
    assert "**Stars**: 500" in text
    assert "stars/day" in text


def test_render_report_hackernews_labels():
    p = Project(
        name="Some HN Story",
        source=Source.HACKER_NEWS,
        url="https://example.com/story",
        stars=197,
        star_velocity=2111.6,
        description="A story",
    )
    report = Report(project=p, draft_model="m", audit_model="m", sections={"TL;DR": "test"}, file_path="")
    text = render_report(report)
    assert "**Score**: 197" in text
    assert "score/day" in text
    assert "**Age**" not in text


def test_render_report_producthunt_labels():
    p = Project(
        name="Cool Tool",
        source=Source.PRODUCT_HUNT,
        url="https://www.producthunt.com/posts/cool-tool",
        stars=450,
        star_velocity=100.0,
        description="A tool",
    )
    report = Report(project=p, draft_model="m", audit_model="m", sections={"TL;DR": "test"}, file_path="")
    text = render_report(report)
    assert "**Votes**: 450" in text
    assert "votes/day" in text
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
    pricing = {"m1": ModelPricing(input_per_million=1.0, output_per_million=2.0)}
    cost = estimate_cost("m1", 1_000_000, 1_000_000, pricing)
    assert cost == 3.0


def test_estimate_cost_without_pricing():
    cost = estimate_cost("unknown-model", 1000, 500)
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


def test_sections_to_text():
    sections = {"TL;DR": "Summary.", "What & Why": "Details."}
    text = sections_to_text(sections)
    assert "## TL;DR" in text
    assert "## What & Why" in text
    assert "Summary." in text


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
