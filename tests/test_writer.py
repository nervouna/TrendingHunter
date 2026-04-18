from datetime import datetime

from trending_hunter.models import Project, Report, Source
from trending_hunter.writer import render_report, save_report
from trending_hunter.cost import estimate_cost, format_cost_report


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
        draft_model="claude-haiku-4-5-20251001",
        audit_model="claude-sonnet-4-5-20250514",
        token_usage={"draft": 300, "audit": 500},
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


def test_estimate_cost():
    cost = estimate_cost("claude-haiku-4-5-20251001", 1000, 500)
    assert cost > 0


def test_format_cost_report():
    token_usage = {"draft": 300, "audit": 500}
    text = format_cost_report(token_usage)
    assert "draft" in text
    assert "audit" in text
