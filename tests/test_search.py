from pathlib import Path

from trending_hunter.search import search_reports


def _write_report(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_search_by_keyword(tmp_path):
    _write_report(
        tmp_path,
        "2026-04-18-github-owner-repo-a.md",
        "# owner/repo-a\n\nThis uses Rust and async.",
    )
    _write_report(
        tmp_path,
        "2026-04-18-github-owner-repo-b.md",
        "# owner/repo-b\n\nPython data pipeline.",
    )
    results = search_reports(str(tmp_path), keyword="Rust")
    assert len(results) == 1
    assert "owner-repo-a" in results[0][0]


def test_search_by_source(tmp_path):
    _write_report(tmp_path, "2026-04-18-github-owner-repo.md", "content")
    _write_report(tmp_path, "2026-04-18-producthunt-launch.md", "content")
    results = search_reports(str(tmp_path), source="github")
    assert len(results) == 1
    assert "github" in results[0][0]


def test_search_combined_filters(tmp_path):
    _write_report(tmp_path, "2026-04-18-github-owner-repo.md", "Rust async runtime")
    _write_report(tmp_path, "2026-04-17-github-other-repo.md", "Python CLI tool")
    results = search_reports(str(tmp_path), keyword="Rust", source="github")
    assert len(results) == 1
    assert "owner-repo" in results[0][0]


def test_search_no_results(tmp_path):
    _write_report(tmp_path, "2026-04-18-github-owner-repo.md", "nothing special")
    results = search_reports(str(tmp_path), keyword="nonexistent")
    assert results == []


def test_search_empty_dir(tmp_path):
    results = search_reports(str(tmp_path), keyword="anything")
    assert results == []


def test_search_nonexistent_dir():
    results = search_reports(
        "/nonexistent/path/that/does/not/exist", keyword="anything"
    )
    assert results == []


# --- date range filtering tests ---


def test_search_by_date_from(tmp_path):
    _write_report(tmp_path, "2026-04-15-github-owner-repo-a.md", "old report")
    _write_report(tmp_path, "2026-04-18-github-owner-repo-b.md", "new report")
    results = search_reports(str(tmp_path), date_from="2026-04-17")
    assert len(results) == 1
    assert "owner-repo-b" in results[0][0]


def test_search_by_date_to(tmp_path):
    _write_report(tmp_path, "2026-04-15-github-owner-repo-a.md", "old report")
    _write_report(tmp_path, "2026-04-18-github-owner-repo-b.md", "new report")
    results = search_reports(str(tmp_path), date_to="2026-04-16")
    assert len(results) == 1
    assert "owner-repo-a" in results[0][0]


def test_search_by_date_range(tmp_path):
    _write_report(tmp_path, "2026-04-10-github-owner-repo-a.md", "too old")
    _write_report(tmp_path, "2026-04-15-github-owner-repo-b.md", "in range")
    _write_report(tmp_path, "2026-04-20-github-owner-repo-c.md", "too new")
    results = search_reports(
        str(tmp_path), date_from="2026-04-12", date_to="2026-04-18"
    )
    assert len(results) == 1
    assert "owner-repo-b" in results[0][0]


def test_search_limit(tmp_path):
    _write_report(tmp_path, "2026-04-18-github-owner-repo-a.md", "report a")
    _write_report(tmp_path, "2026-04-18-github-owner-repo-b.md", "report b")
    _write_report(tmp_path, "2026-04-18-github-owner-repo-c.md", "report c")
    results = search_reports(str(tmp_path), limit=2)
    assert len(results) == 2


def test_search_date_with_no_match(tmp_path):
    _write_report(tmp_path, "2026-04-18-github-owner-repo.md", "content")
    results = search_reports(str(tmp_path), date_from="2026-05-01")
    assert results == []


def test_search_case_insensitive(tmp_path):
    _write_report(
        tmp_path, "2026-04-18-github-owner-repo.md", "this project uses rust and tokio"
    )
    results = search_reports(str(tmp_path), keyword="Rust")
    assert len(results) == 1
    assert "owner-repo" in results[0][0]
