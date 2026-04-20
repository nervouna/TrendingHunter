from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from click.testing import CliRunner

from trending_hunter.cli import cli, run_cycle


@patch("trending_hunter.cli.run_cycle")
@patch("time.sleep")
def test_schedule_runs_cycles(mock_sleep, mock_run_cycle):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "schedule",
        "--interval", "60",
        "--cycles", "3",
        "--source", "github",
    ])
    assert result.exit_code == 0, result.output
    assert mock_run_cycle.call_count == 3
    assert mock_sleep.call_count == 2  # sleeps between cycles, not after last


@patch("trending_hunter.cli.run_cycle")
def test_run_passes_language_to_run_cycle(mock_run_cycle):
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--language", "chinese"])
    assert result.exit_code == 0, result.output
    mock_run_cycle.assert_called_once()
    language = mock_run_cycle.call_args[1]["language"]
    assert language == "chinese"


@patch("trending_hunter.cli.run_cycle")
def test_run_language_short_flag(mock_run_cycle):
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "-l", "japanese"])
    assert result.exit_code == 0, result.output
    mock_run_cycle.assert_called_once()
    language = mock_run_cycle.call_args[1]["language"]
    assert language == "japanese"


@patch("trending_hunter.cli.run_cycle")
def test_run_language_default_empty(mock_run_cycle):
    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code == 0, result.output
    mock_run_cycle.assert_called_once()
    language = mock_run_cycle.call_args[1]["language"]
    assert language == ""


@patch("trending_hunter.cli.load_config")
def test_run_cycle_unknown_source(mock_load, capsys):
    """run_cycle with unknown source prints error and returns."""
    mock_load.return_value = MagicMock()
    run_cycle("nonexistent", "config.yaml", 0, False)
    captured = capsys.readouterr()
    assert "Unknown source" in captured.out


@patch("trending_hunter.cli.load_config")
def test_run_cycle_source_disabled(mock_load):
    settings = MagicMock()
    settings.sources.github.enabled = False
    settings.proxy = ""
    mock_load.return_value = settings
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert "disabled" in result.output


@patch("trending_hunter.cli.load_config")
def test_run_cycle_no_source_config(mock_load):
    class NoAttrSources:
        pass
    settings = MagicMock()
    settings.sources = NoAttrSources()
    mock_load.return_value = settings

    import trending_hunter.cli as cli_mod
    original_fetchers = cli_mod._FETCHERS
    cli_mod._FETCHERS = {**original_fetchers, "nonexistent": MagicMock()}
    try:
        run_cycle("nonexistent", "config.yaml", 0, False)
    finally:
        cli_mod._FETCHERS = original_fetchers


@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.fetch_trending", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_dry_run(mock_load, mock_fetch, mock_filter):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    settings.signal_gate.min_star_velocity = 0
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source
    proj = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )
    mock_fetch.return_value = [proj]
    mock_filter.return_value = [proj]

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github", "--dry-run"])
    assert result.exit_code == 0
    assert "owner/repo" in result.output


@patch("trending_hunter.cli.run_pipeline")
@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.fetch_trending")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_results(mock_load, mock_fetch, mock_filter, mock_pipeline):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source, TokenUsage
    from trending_hunter.pipeline import PipelineResult
    proj = Project(name="owner/repo", source=Source.GITHUB, url="https://github.com/owner/repo", stars=100, star_velocity=10.0, description="test")
    mock_fetch.return_value = [proj]
    mock_filter.return_value = [proj]

    result_obj = PipelineResult(
        project=proj,
        token_usage={"draft": TokenUsage(input_tokens=50, output_tokens=100)},
        file_path="/tmp/test.md",
        cost=0.0012,
    )
    mock_pipeline.return_value = [result_obj]

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert result.exit_code == 0
    assert "Saved:" in result.output
    assert "Cost:" in result.output


@patch("trending_hunter.cli.run_pipeline")
@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.fetch_trending")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_error(mock_load, mock_fetch, mock_filter, mock_pipeline):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source
    from trending_hunter.pipeline import PipelineResult
    proj = Project(name="owner/repo", source=Source.GITHUB, url="https://github.com/owner/repo", stars=100, star_velocity=10.0, description="test")
    mock_fetch.return_value = [proj]
    mock_filter.return_value = [proj]

    result_obj = PipelineResult(project=proj, error="LLM failed", status="error")
    mock_pipeline.return_value = [result_obj]

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert result.exit_code == 0
    assert "ERROR:" in result.output


@patch("trending_hunter.cli.run_pipeline")
@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.fetch_trending")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_skipped(mock_load, mock_fetch, mock_filter, mock_pipeline):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source
    from trending_hunter.pipeline import PipelineResult
    proj = Project(name="owner/repo", source=Source.GITHUB, url="https://github.com/owner/repo", stars=100, star_velocity=10.0, description="test")
    mock_fetch.return_value = [proj]
    mock_filter.return_value = [proj]

    result_obj = PipelineResult(project=proj, file_path="/tmp/test.md", status="skipped")
    mock_pipeline.return_value = [result_obj]

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert result.exit_code == 0
    assert "SKIPPED:" in result.output


@patch("trending_hunter.cli.load_config")
def test_run_cycle_not_implemented(mock_load, capsys):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    import trending_hunter.cli as cli_mod
    original_fetchers = cli_mod._FETCHERS
    cli_mod._FETCHERS = {**original_fetchers, "github": MagicMock(side_effect=NotImplementedError("Not available"))}
    try:
        run_cycle("github", "config.yaml", 0, False)
        captured = capsys.readouterr()
        assert "Not available" in captured.out
    finally:
        cli_mod._FETCHERS = original_fetchers


@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.fetch_trending")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_limit(mock_load, mock_fetch, mock_filter):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source
    proj1 = Project(name="a/b", source=Source.GITHUB, url="https://github.com/a/b", stars=100, star_velocity=10.0, description="test1")
    proj2 = Project(name="c/d", source=Source.GITHUB, url="https://github.com/c/d", stars=200, star_velocity=20.0, description="test2")
    mock_fetch.return_value = [proj1, proj2]
    mock_filter.return_value = [proj1, proj2]

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github", "--limit", "1", "--dry-run"])
    assert result.exit_code == 0
    assert "Limited to 1" in result.output


@patch("trending_hunter.cli.search_reports", return_value=[("file.md", "excerpt")])
@patch("trending_hunter.cli.load_config")
def test_search_command(mock_load, mock_search):
    settings = MagicMock()
    settings.knowledge_base.path = "./reports"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--keyword", "test"])
    assert result.exit_code == 0
    assert "Found 1 report(s)" in result.output


@patch("trending_hunter.cli.search_reports", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_search_command_no_results(mock_load, mock_search):
    settings = MagicMock()
    settings.knowledge_base.path = "./reports"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--keyword", "nothing"])
    assert result.exit_code == 0
    assert "No matching reports found." in result.output


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_hacker_news(mock_load, mock_filter, mock_pipeline, capsys):
    settings = MagicMock()
    settings.sources.hacker_news.enabled = True
    settings.sources.hacker_news.top_n = 5
    settings.proxy = ""
    mock_load.return_value = settings

    import trending_hunter.cli as cli_mod
    original_fetchers = cli_mod._FETCHERS
    mock_fetch = MagicMock(return_value=[])
    cli_mod._FETCHERS = {**original_fetchers, "hacker_news": mock_fetch}
    try:
        run_cycle("hacker_news", "config.yaml", 0, False)
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args[1]["top_n"] == 5
    finally:
        cli_mod._FETCHERS = original_fetchers


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_product_hunt(mock_load, mock_filter, mock_pipeline, capsys):
    settings = MagicMock()
    settings.sources.product_hunt.enabled = True
    settings.sources.product_hunt.token = "ph-token"
    settings.sources.product_hunt.top_n = 10
    settings.proxy = ""
    mock_load.return_value = settings

    import trending_hunter.cli as cli_mod
    original_fetchers = cli_mod._FETCHERS
    mock_fetch = MagicMock(return_value=[])
    cli_mod._FETCHERS = {**original_fetchers, "product_hunt": mock_fetch}
    try:
        run_cycle("product_hunt", "config.yaml", 0, False)
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args[1]["token"] == "ph-token"
        assert mock_fetch.call_args[1]["top_n"] == 10
    finally:
        cli_mod._FETCHERS = original_fetchers
