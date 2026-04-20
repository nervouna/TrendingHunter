from __future__ import annotations

from unittest.mock import patch


def test_main_invokes_cli():
    with patch("trending_hunter.cli.cli") as mock_cli:
        import trending_hunter.__main__  # noqa: F401
    mock_cli.assert_called_once()
