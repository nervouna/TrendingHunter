from unittest.mock import patch

import pytest

from tests.conftest import (
    _make_project as _sample_project,
)
from tests.conftest import (
    _mock_sections,
)
from trending_hunter.dedup import SeenUrls
from trending_hunter.pipeline import PipelineResult, run_pipeline
from trending_hunter.settings import (
    KnowledgeBaseConfig,
    LLMConfig,
    LLMStageConfig,
    Settings,
    SignalGateConfig,
    SourcesConfig,
    TavilyConfig,
)


def _sample_settings() -> Settings:
    return Settings(
        sources=SourcesConfig(),
        signal_gate=SignalGateConfig(),
        llm=LLMConfig(
            draft=LLMStageConfig(api_key="k", model="draft-model", timeout=120.0),
            audit=LLMStageConfig(api_key="k", model="audit-model", timeout=300.0),
            rewrite=LLMStageConfig(api_key="k", model="rewrite-model", timeout=120.0),
        ),
        tavily=TavilyConfig(api_key="tavily-key"),
        knowledge_base=KnowledgeBaseConfig(path="./reports"),
    )


MOCK_DRAFT = (_mock_sections(), {"input": 100, "output": 200})
MOCK_AUDIT = (_mock_sections(), {"input": 150, "output": 250})
MOCK_REWRITE = (_mock_sections(), {"input": 80, "output": 150})


@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_returns_results(
    mock_draft, mock_audit, mock_rewrite, mock_save, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()
    projects = [_sample_project()]

    results = run_pipeline(projects, settings)

    assert len(results) == 1
    r = results[0]
    assert isinstance(r, PipelineResult)
    assert r.error is None
    assert r.project.name == "owner/repo"
    assert r.token_usage["draft"].input_tokens == 100
    assert r.token_usage["audit"].input_tokens == 150
    assert r.token_usage["rewrite"].input_tokens == 80
    assert len(r.run_id) == 8
    assert r.duration_seconds >= 0
    assert set(r.stage_durations) == {"draft", "audit", "rewrite"}


@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_multiple_projects(
    mock_draft, mock_audit, mock_rewrite, mock_save, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()
    projects = [_sample_project("a/b"), _sample_project("c/d")]

    results = run_pipeline(projects, settings)

    assert len(results) == 2
    assert results[0].error is None
    assert results[1].error is None


@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch(
    "trending_hunter.pipeline.generate_draft",
    side_effect=[RuntimeError("LLM down"), MOCK_DRAFT],
)
def test_run_pipeline_partial_failure(
    mock_draft, mock_audit, mock_rewrite, mock_save, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()
    projects = [_sample_project("a/b"), _sample_project("c/d")]

    results = run_pipeline(projects, settings)

    assert len(results) == 2
    assert results[0].error is not None
    assert "LLM down" in results[0].error
    mock_audit.assert_called_once()
    assert results[1].error is None


@pytest.mark.parametrize("language", ["chinese", ""])
@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_passes_language_to_stages(
    mock_draft, mock_audit, mock_rewrite, mock_save, language, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()
    projects = [_sample_project()]

    run_pipeline(projects, settings, language=language)

    mock_draft.assert_called_once()
    assert mock_draft.call_args[1]["language"] == language
    mock_audit.assert_called_once()
    assert mock_audit.call_args[1]["language"] == language
    mock_rewrite.assert_called_once()
    assert mock_rewrite.call_args[1]["language"] == language


@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_skips_seen_url(
    mock_draft, mock_audit, mock_rewrite, mock_save, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()

    project = _sample_project("owner/repo")
    seen = SeenUrls(tmp_path / ".seen_urls.json")
    seen.mark_seen(project.normalized_url)

    results = run_pipeline([project], settings, seen=seen)

    mock_draft.assert_not_called()
    assert len(results) == 1
    assert results[0].status == "skipped"


def test_run_pipeline_keyboard_interrupt_saves_seen(tmp_path):
    """Problem 1: seen.save() must run even on KeyboardInterrupt."""
    settings = _sample_settings()
    p1 = _sample_project("owner/repo1")
    p2 = _sample_project("owner/repo2")

    seen = SeenUrls(tmp_path / ".seen_urls.json")

    draft_call = 0

    def draft_side_effect(*args, **kwargs):
        nonlocal draft_call
        draft_call += 1
        if draft_call == 2:
            raise KeyboardInterrupt()
        return MOCK_DRAFT

    with (
        patch("trending_hunter.pipeline.generate_draft", side_effect=draft_side_effect),
        patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT),
        patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE),
        patch(
            "trending_hunter.pipeline.save_report", return_value=tmp_path / "report.md"
        ),
    ):
        try:
            run_pipeline([p1, p2], settings, seen=seen)
        except KeyboardInterrupt:
            pass

    # seen.save() should have been called despite the interrupt
    assert seen._path.exists()
    assert seen.is_seen(p1.normalized_url)


@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_dedup_within_cycle(
    mock_draft, mock_audit, mock_rewrite, mock_save, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()

    p1 = _sample_project("owner/repo")
    p2 = _sample_project("owner/repo")  # duplicate

    seen = SeenUrls(tmp_path / ".seen_urls.json")
    results = run_pipeline([p1, p2], settings, seen=seen)

    assert mock_draft.call_count == 1
    assert len(results) == 2
    assert results[0].status == "success"
    assert results[1].status == "skipped"


@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report")
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_skip_rewrite(
    mock_draft, mock_audit, mock_rewrite, mock_save, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()
    projects = [_sample_project()]

    results = run_pipeline(projects, settings, skip_rewrite=True)

    mock_draft.assert_called_once()
    mock_audit.assert_called_once()
    mock_rewrite.assert_not_called()
    assert len(results) == 1
    assert results[0].error is None
    # sections should come from audit, not rewrite
    saved_report = mock_save.call_args[0][0]
    assert saved_report.sections == MOCK_AUDIT[0]


@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_rewrite_enabled_by_default(
    mock_draft, mock_audit, mock_rewrite, mock_save, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()
    projects = [_sample_project()]

    results = run_pipeline(projects, settings)

    mock_rewrite.assert_called_once()
    assert len(results) == 1


@patch("trending_hunter.pipeline.clear_cache")
@patch("trending_hunter.pipeline.save_report")
@patch("trending_hunter.pipeline.rewrite_report", return_value=MOCK_REWRITE)
@patch("trending_hunter.pipeline.audit_report", return_value=MOCK_AUDIT)
@patch("trending_hunter.pipeline.generate_draft", return_value=MOCK_DRAFT)
def test_run_pipeline_clears_cache(
    mock_draft, mock_audit, mock_rewrite, mock_save, mock_clear, tmp_path
):
    mock_save.return_value = tmp_path / "report.md"
    settings = _sample_settings()
    projects = [_sample_project()]

    run_pipeline(projects, settings)

    mock_clear.assert_called_once()
