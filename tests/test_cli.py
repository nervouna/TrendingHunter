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
