from unittest.mock import patch

from click.testing import CliRunner

from trending_hunter.cli import cli


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
