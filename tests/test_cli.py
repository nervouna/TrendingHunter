from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from trending_hunter.cli import _resolve_fetcher_args, cli, run_cycle
from trending_hunter.models import Source


@patch("trending_hunter.cli.run_cycle")
@patch("trending_hunter.cli.load_config")
@patch("time.sleep")
def test_schedule_runs_cycles(mock_sleep, mock_load, mock_run_cycle):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "schedule",
            "--interval",
            "60",
            "--cycles",
            "3",
            "--source",
            "github",
        ],
    )
    assert result.exit_code == 0, result.output
    assert mock_run_cycle.call_count == 3
    assert mock_sleep.call_count == 2


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
def test_run_cycle_no_source_config(mock_load, patched_fetchers):
    class NoAttrSources:
        pass

    settings = MagicMock()
    settings.sources = NoAttrSources()
    mock_load.return_value = settings

    patched_fetchers["nonexistent"] = MagicMock()
    run_cycle("nonexistent", "config.yaml", 0, False)


@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_dry_run(mock_load, mock_filter, patched_fetchers):
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
    mock_filter.return_value = [proj]

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = [proj]
    patched_fetchers["github"] = mock_fetcher

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github", "--dry-run"])
    assert result.exit_code == 0
    assert "owner/repo" in result.output


@patch("trending_hunter.cli.run_pipeline")
@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_results(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source, TokenUsage
    from trending_hunter.pipeline import PipelineResult

    proj = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )
    mock_filter.return_value = [proj]

    result_obj = PipelineResult(
        project=proj,
        token_usage={"draft": TokenUsage(input_tokens=50, output_tokens=100)},
        file_path="/tmp/test.md",
        cost=0.0012,
    )
    mock_pipeline.return_value = [result_obj]

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = [proj]
    patched_fetchers["github"] = mock_fetcher

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert result.exit_code == 0
    assert "Saved:" in result.output
    assert "Cost:" in result.output


@patch("trending_hunter.cli.run_pipeline")
@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_error(mock_load, mock_filter, mock_pipeline, patched_fetchers):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source
    from trending_hunter.pipeline import PipelineResult

    proj = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )
    mock_filter.return_value = [proj]

    result_obj = PipelineResult(project=proj, error="LLM failed", status="error")
    mock_pipeline.return_value = [result_obj]

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = [proj]
    patched_fetchers["github"] = mock_fetcher

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert result.exit_code == 0
    assert "ERROR:" in result.output


@patch("trending_hunter.cli.run_pipeline")
@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_skipped(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source
    from trending_hunter.pipeline import PipelineResult

    proj = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )
    mock_filter.return_value = [proj]

    result_obj = PipelineResult(
        project=proj, file_path="/tmp/test.md", status="skipped"
    )
    mock_pipeline.return_value = [result_obj]

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = [proj]
    patched_fetchers["github"] = mock_fetcher

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert result.exit_code == 0
    assert "SKIPPED:" in result.output


@patch("trending_hunter.cli.load_config")
def test_run_cycle_not_implemented(mock_load, capsys, patched_fetchers):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.side_effect = NotImplementedError("Not available")
    patched_fetchers["github"] = mock_fetcher
    run_cycle("github", "config.yaml", 0, False)
    captured = capsys.readouterr()
    assert "Not available" in captured.out


@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_with_limit(mock_load, mock_filter, patched_fetchers):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source

    proj1 = Project(
        name="a/b",
        source=Source.GITHUB,
        url="https://github.com/a/b",
        stars=100,
        star_velocity=10.0,
        description="test1",
    )
    proj2 = Project(
        name="c/d",
        source=Source.GITHUB,
        url="https://github.com/c/d",
        stars=200,
        star_velocity=20.0,
        description="test2",
    )
    mock_filter.return_value = [proj1, proj2]

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = [proj1, proj2]
    patched_fetchers["github"] = mock_fetcher

    runner = CliRunner()
    result = runner.invoke(
        cli, ["run", "--source", "github", "--limit", "1", "--dry-run"]
    )
    assert result.exit_code == 0
    assert "Limited to 1" in result.output


@patch("trending_hunter.cli.load_config")
def test_run_cycle_generic_exception(mock_load, capsys, patched_fetchers):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.side_effect = ConnectionError("Network unreachable")
    patched_fetchers["github"] = mock_fetcher
    run_cycle("github", "config.yaml", 0, False)
    captured = capsys.readouterr()
    assert "Fetcher error" in captured.out
    assert "Network unreachable" in captured.out


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
def test_run_cycle_hacker_news(mock_load, mock_filter, mock_pipeline, patched_fetchers):
    settings = MagicMock()
    settings.sources.hacker_news.enabled = True
    settings.sources.hacker_news.top_n = 5
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = []
    patched_fetchers["hacker_news"] = mock_fetcher
    run_cycle("hacker_news", "config.yaml", 0, False)
    mock_fetcher.fetch.assert_called_once()
    assert mock_fetcher.fetch.call_args[0][0] is settings


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_product_hunt(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.product_hunt.enabled = True
    settings.sources.product_hunt.token = "ph-token"
    settings.sources.product_hunt.top_n = 10
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = []
    patched_fetchers["product_hunt"] = mock_fetcher
    run_cycle("product_hunt", "config.yaml", 0, False)
    mock_fetcher.fetch.assert_called_once()
    assert mock_fetcher.fetch.call_args[0][0] is settings


def test_resolve_fetcher_args_unknown_source():
    settings = MagicMock()
    fetcher, error = _resolve_fetcher_args("unknown", settings)
    assert fetcher is None
    assert "Unknown source" in error


def test_resolve_fetcher_args_disabled_source():
    settings = MagicMock()
    settings.sources.github.enabled = False
    settings.proxy = ""
    fetcher, error = _resolve_fetcher_args("github", settings)
    assert fetcher is None
    assert "disabled" in error


def test_resolve_fetcher_args_missing_config():
    class NoAttrSources:
        pass

    settings = MagicMock()
    settings.sources = NoAttrSources()
    fetcher, error = _resolve_fetcher_args("github", settings)
    assert fetcher is None
    assert "No configuration" in error


def test_resolve_fetcher_args_github():
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = "python"
    settings.sources.github.since = "daily"
    settings.proxy = "http://proxy:8080"
    fetcher, error = _resolve_fetcher_args("github", settings)
    assert fetcher is not None
    assert error is None
    from trending_hunter.fetchers.github import GitHubFetcher

    assert isinstance(fetcher, GitHubFetcher)


def test_resolve_fetcher_args_hacker_news():
    settings = MagicMock()
    settings.sources.hacker_news.enabled = True
    settings.sources.hacker_news.top_n = 15
    settings.proxy = ""
    fetcher, error = _resolve_fetcher_args("hacker_news", settings)
    assert fetcher is not None
    assert error is None
    from trending_hunter.fetchers.hackernews import HackerNewsFetcher

    assert isinstance(fetcher, HackerNewsFetcher)


def test_resolve_fetcher_args_product_hunt():
    settings = MagicMock()
    settings.sources.product_hunt.enabled = True
    settings.sources.product_hunt.token = "ph-123"
    settings.sources.product_hunt.top_n = 20
    settings.proxy = ""
    fetcher, error = _resolve_fetcher_args("product_hunt", settings)
    assert fetcher is not None
    assert error is None
    from trending_hunter.fetchers.producthunt import ProductHuntFetcher

    assert isinstance(fetcher, ProductHuntFetcher)


@patch("trending_hunter.cli.run_cycle")
def test_run_passes_no_rewrite(mock_run_cycle):
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--no-rewrite"])
    assert result.exit_code == 0, result.output
    mock_run_cycle.assert_called_once()
    assert mock_run_cycle.call_args[1]["skip_rewrite"] is True


@patch("trending_hunter.cli.run_cycle")
def test_run_rewrite_enabled_by_default(mock_run_cycle):
    runner = CliRunner()
    result = runner.invoke(cli, ["run"])
    assert result.exit_code == 0, result.output
    mock_run_cycle.assert_called_once()
    assert mock_run_cycle.call_args[1]["skip_rewrite"] is False


@patch("trending_hunter.cli.run_cycle")
@patch("trending_hunter.cli.load_config")
@patch("time.sleep")
def test_schedule_shutdown_on_signal(mock_sleep, mock_load, mock_run_cycle):
    import threading

    import trending_hunter.cli as cli_mod

    original_event = cli_mod._shutdown_event
    cli_mod._shutdown_event = threading.Event()
    try:
        cli_mod._shutdown_event.set()
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schedule",
                "--interval",
                "60",
                "--source",
                "github",
            ],
        )
        assert result.exit_code == 0, result.output
        assert mock_run_cycle.call_count == 0
    finally:
        cli_mod._shutdown_event = original_event


@patch("trending_hunter.cli.run_cycle")
@patch("trending_hunter.cli.load_config")
@patch("time.sleep")
def test_schedule_backoff_on_error(mock_sleep, mock_load, mock_run_cycle):
    import trending_hunter.cli as cli_mod

    original_backoff = cli_mod._consecutive_failures
    cli_mod._consecutive_failures = 0
    try:
        mock_run_cycle.side_effect = [Exception("fail"), None]
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schedule",
                "--interval",
                "60",
                "--cycles",
                "2",
                "--source",
                "github",
            ],
        )
        assert result.exit_code == 0, result.output
        assert mock_sleep.call_args_list[0] == call(120)
    finally:
        cli_mod._consecutive_failures = original_backoff


@patch("trending_hunter.cli.run_cycle")
@patch("trending_hunter.cli.load_config")
@patch("time.sleep")
def test_schedule_backoff_capped(mock_sleep, mock_load, mock_run_cycle):
    import trending_hunter.cli as cli_mod

    original_backoff = cli_mod._consecutive_failures
    cli_mod._consecutive_failures = 0
    try:
        mock_run_cycle.side_effect = [Exception("fail")] * 5 + [None]
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schedule",
                "--interval",
                "60",
                "--cycles",
                "6",
                "--source",
                "github",
            ],
        )
        assert result.exit_code == 0, result.output
        sleep_intervals = [c.args[0] for c in mock_sleep.call_args_list]
        assert all(i <= 300 for i in sleep_intervals)
        assert 300 in sleep_intervals
    finally:
        cli_mod._consecutive_failures = original_backoff


@patch("trending_hunter.cli.run_cycle")
@patch("time.sleep")
def test_schedule_config_loaded_once(mock_sleep, mock_run_cycle):
    with patch("trending_hunter.cli.load_config") as mock_load:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "schedule",
                "--interval",
                "60",
                "--cycles",
                "2",
                "--source",
                "github",
            ],
        )
        assert result.exit_code == 0, result.output
        assert mock_load.call_count == 1


@patch(
    "trending_hunter.cli.search_reports",
    return_value=[("2026-04-18-file.md", "excerpt")],
)
@patch("trending_hunter.cli.load_config")
def test_search_command_with_date_from(mock_load, mock_search):
    settings = MagicMock()
    settings.knowledge_base.path = "./reports"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--keyword", "test", "--from", "2026-04-15"])
    assert result.exit_code == 0
    mock_search.assert_called_once_with(
        base_dir="./reports",
        keyword="test",
        source=None,
        date_from="2026-04-15",
        date_to=None,
        limit=0,
    )


@patch(
    "trending_hunter.cli.search_reports",
    return_value=[("2026-04-18-file.md", "excerpt")],
)
@patch("trending_hunter.cli.load_config")
def test_search_command_with_date_to(mock_load, mock_search):
    settings = MagicMock()
    settings.knowledge_base.path = "./reports"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--keyword", "test", "--to", "2026-04-20"])
    assert result.exit_code == 0
    mock_search.assert_called_once_with(
        base_dir="./reports",
        keyword="test",
        source=None,
        date_from=None,
        date_to="2026-04-20",
        limit=0,
    )


@patch(
    "trending_hunter.cli.search_reports",
    return_value=[("2026-04-18-file.md", "excerpt")],
)
@patch("trending_hunter.cli.load_config")
def test_search_command_with_limit(mock_load, mock_search):
    settings = MagicMock()
    settings.knowledge_base.path = "./reports"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["search", "--keyword", "test", "--limit", "5"])
    assert result.exit_code == 0
    mock_search.assert_called_once_with(
        base_dir="./reports",
        keyword="test",
        source=None,
        date_from=None,
        date_to=None,
        limit=5,
    )


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_passes_source_to_filter(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = []
    patched_fetchers["github"] = mock_fetcher

    run_cycle("github", "config.yaml", 0, False)

    mock_filter.assert_called_once()
    call_args = mock_filter.call_args
    assert (
        call_args[1].get("source") == Source.GITHUB
        or call_args[0][2] == Source.GITHUB
    )


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_passes_hacker_news_source(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.hacker_news.enabled = True
    settings.sources.hacker_news.top_n = 10
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = []
    patched_fetchers["hacker_news"] = mock_fetcher

    run_cycle("hacker_news", "config.yaml", 0, False)

    mock_filter.assert_called_once()
    call_args = mock_filter.call_args
    source_arg = call_args[1].get("source") or call_args[0][2]
    assert source_arg == Source.HACKER_NEWS


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_passes_product_hunt_source(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.product_hunt.enabled = True
    settings.sources.product_hunt.token = "ph-token"
    settings.sources.product_hunt.top_n = 10
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = []
    patched_fetchers["product_hunt"] = mock_fetcher

    run_cycle("product_hunt", "config.yaml", 0, False)

    mock_filter.assert_called_once()
    call_args = mock_filter.call_args
    source_arg = call_args[1].get("source") or call_args[0][2]
    assert source_arg == Source.PRODUCT_HUNT


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_uses_fetcher_protocol(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = []
    patched_fetchers["github"] = mock_fetcher

    run_cycle("github", "config.yaml", 0, False)

    mock_fetcher.fetch.assert_called_once_with(settings)


@patch("trending_hunter.cli.run_pipeline", return_value=[])
@patch("trending_hunter.cli.filter_projects", return_value=[])
@patch("trending_hunter.cli.load_config")
def test_run_cycle_loads_config_once(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = []
    patched_fetchers["github"] = mock_fetcher

    run_cycle("github", "config.yaml", 0, False)

    assert mock_load.call_count == 1


@patch("trending_hunter.cli.run_pipeline")
@patch("trending_hunter.cli.filter_projects")
@patch("trending_hunter.cli.load_config")
def test_run_cycle_empty_path_no_saved_line(
    mock_load, mock_filter, mock_pipeline, patched_fetchers
):
    settings = MagicMock()
    settings.sources.github.enabled = True
    settings.sources.github.language = ""
    settings.sources.github.since = "daily"
    settings.proxy = ""
    mock_load.return_value = settings

    from trending_hunter.models import Project, Source, TokenUsage
    from trending_hunter.pipeline import PipelineResult

    proj = Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=100,
        star_velocity=10.0,
        description="test",
    )

    result_obj = PipelineResult(
        project=proj,
        token_usage={"draft": TokenUsage(input_tokens=50, output_tokens=100)},
        file_path="",
        cost=0.0012,
    )
    mock_pipeline.return_value = [result_obj]

    mock_fetcher = MagicMock()
    mock_fetcher.fetch.return_value = [proj]
    patched_fetchers["github"] = mock_fetcher

    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--source", "github"])
    assert result.exit_code == 0
    assert "Saved:" not in result.output


@patch("trending_hunter.cli.load_config")
def test_doctor_all_pass(mock_load):
    settings = MagicMock()
    settings.knowledge_base.path = "/tmp/kb"
    settings.llm.draft.base_url = "http://localhost"
    settings.llm.draft.api_key = "key1"
    settings.llm.draft.model = "model-a"
    settings.llm.audit.base_url = "http://localhost"
    settings.llm.audit.api_key = "key2"
    settings.llm.audit.model = "model-a"
    settings.llm.rewrite.base_url = "http://localhost"
    settings.llm.rewrite.api_key = "key3"
    settings.llm.rewrite.model = "model-a"
    settings.model_pricing = {}
    settings.tavily.api_key = "tavily-key"
    settings.sources.product_hunt.token = "ph-token"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "✔ LLM Config" in result.output
    assert "✔ Tavily API Key" in result.output
    assert "✔ Product API Token" in result.output
    assert "✖" not in result.output


@patch("trending_hunter.cli.load_config")
def test_doctor_llm_missing_fields(mock_load):
    settings = MagicMock()
    settings.knowledge_base.path = "/tmp/kb"
    settings.llm.draft.base_url = "http://localhost"
    settings.llm.draft.api_key = "key1"
    settings.llm.draft.model = "model-a"
    settings.llm.audit.base_url = ""
    settings.llm.audit.api_key = ""
    settings.llm.audit.model = ""
    settings.llm.rewrite.base_url = "http://localhost"
    settings.llm.rewrite.api_key = "key3"
    settings.llm.rewrite.model = "model-a"
    settings.model_pricing = {}
    settings.tavily.api_key = "tavily-key"
    settings.sources.product_hunt.token = "ph-token"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "✖ LLM Config" in result.output
    assert "Audit provider" in result.output
    assert "missing" in result.output


@patch("trending_hunter.cli.load_config")
def test_doctor_product_token_missing(mock_load):
    settings = MagicMock()
    settings.knowledge_base.path = "/tmp/kb"
    settings.llm.draft.base_url = "http://localhost"
    settings.llm.draft.api_key = "key1"
    settings.llm.draft.model = "model-a"
    settings.llm.audit.base_url = "http://localhost"
    settings.llm.audit.api_key = "key2"
    settings.llm.audit.model = "model-a"
    settings.llm.rewrite.base_url = "http://localhost"
    settings.llm.rewrite.api_key = "key3"
    settings.llm.rewrite.model = "model-a"
    settings.model_pricing = {}
    settings.tavily.api_key = "tavily-key"
    settings.sources.product_hunt.token = ""
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "✖ Product API Token" in result.output


@patch("trending_hunter.cli.load_config")
def test_doctor_config_load_fail(mock_load):
    mock_load.side_effect = FileNotFoundError("config.yaml not found")
    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert result.exit_code == 0
    assert "Failed to load config" in result.output


@patch("trending_hunter.cli.load_config")
def test_doctor_shows_pricing(mock_load):
    from trending_hunter.settings import ModelPricing

    settings = MagicMock()
    settings.knowledge_base.path = "/tmp/kb"
    settings.llm.draft.base_url = "http://localhost"
    settings.llm.draft.api_key = "key1"
    settings.llm.draft.model = "gpt-4"
    settings.llm.audit.base_url = "http://localhost"
    settings.llm.audit.api_key = "key2"
    settings.llm.audit.model = "gpt-4"
    settings.llm.rewrite.base_url = "http://localhost"
    settings.llm.rewrite.api_key = "key3"
    settings.llm.rewrite.model = "gpt-4"
    settings.model_pricing = {
        "draft": ModelPricing(input_per_million=10.0, output_per_million=30.0)
    }
    settings.tavily.api_key = "tavily-key"
    settings.sources.product_hunt.token = "ph-token"
    mock_load.return_value = settings

    runner = CliRunner()
    result = runner.invoke(cli, ["doctor"])
    assert "$10.0/30.0 per 1M" in result.output
