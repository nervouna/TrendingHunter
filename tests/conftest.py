from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def enrich_stub():
    mock_content = "# Test Repo\nThis is a test README."

    with patch(
        "trending_hunter.collector._tavily_extract",
        return_value=mock_content,
    ):
        yield
