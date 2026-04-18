from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def enrich_stub():
    created = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%dT%H:%M:%SZ")
    meta_json = {
        "created_at": created,
        "stargazers_count": 100,
        "description": "test",
        "subscribers_count": 5,
        "forks_count": 10,
        "open_issues_count": 3,
        "language": "Python",
    }
    contributors_json = [
        {"login": "alice", "contributions": 50},
        {"login": "bob", "contributions": 1},
        {"login": "carol", "contributions": 1},
    ]

    def _mock_github_get(path: str, **kwargs: object) -> MagicMock:
        resp = MagicMock()
        if "/readme" in path:
            resp.text = "# Test README"
            resp.json.side_effect = ValueError
        elif "/contributors" in path:
            resp.json.return_value = contributors_json
            resp.text = ""
        else:
            resp.json.return_value = meta_json
            resp.text = ""
        return resp

    with patch("trending_hunter.collector._github_get", side_effect=_mock_github_get):
        yield
