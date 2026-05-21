from unittest.mock import MagicMock, patch

import httpx
import pytest

from trending_hunter.llm.tools import clear_cache, tavily_extract, tavily_search


def _mock_client(resp: MagicMock | None = None) -> MagicMock:
    """Create a mock httpx client with the given response."""
    mock_cli = MagicMock()
    mock_cli.request.return_value = resp or MagicMock()
    return mock_cli


def test_tavily_search_returns_text():
    clear_cache()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Test",
                "content": "A test result.",
                "url": "https://example.com",
            },
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_cli = _mock_client(mock_resp)

    with patch("trending_hunter.llm.tools._get_client", return_value=mock_cli):
        result = tavily_search("test query", "fake-key")
        assert "Test" in result
        assert "A test result" in result
        assert mock_cli.request.call_count == 1

        # second call should use cache
        result2 = tavily_search("test query", "fake-key")
        assert result2 == result
        assert mock_cli.request.call_count == 1


def test_tavily_extract_returns_content():
    clear_cache()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [{"raw_content": "# README\nHello world."}]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_cli = _mock_client(mock_resp)

    with patch("trending_hunter.llm.tools._get_client", return_value=mock_cli):
        result = tavily_extract("https://github.com/x/y", "fake-key")
        assert "README" in result
        assert mock_cli.request.call_count == 1

        # cache hit
        tavily_extract("https://github.com/x/y", "fake-key")
        assert mock_cli.request.call_count == 1


def test_tavily_extract_different_urls_not_cached():
    clear_cache()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [{"raw_content": "content"}]}
    mock_resp.raise_for_status = MagicMock()
    mock_cli = _mock_client(mock_resp)

    with patch("trending_hunter.llm.tools._get_client", return_value=mock_cli):
        tavily_extract("https://a.com", "key")
        tavily_extract("https://b.com", "key")
        assert mock_cli.request.call_count == 2


def test_tavily_search_retries_on_http_status_error():
    """Test that tavily_search retries on HTTP status errors."""
    clear_cache()
    mock_resp_success = MagicMock()
    mock_resp_success.json.return_value = {
        "results": [
            {"title": "Test", "content": "Success", "url": "https://example.com"}
        ]
    }
    mock_resp_success.raise_for_status = MagicMock()

    mock_resp_error = MagicMock()
    mock_resp_error.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )

    mock_cli = MagicMock()
    mock_cli.request.side_effect = [mock_resp_error, mock_resp_success]

    with (
        patch("trending_hunter.llm.tools._get_client", return_value=mock_cli),
        patch("trending_hunter.llm.tools.time.sleep"),
    ):
        result = tavily_search("test", "key")
        assert "Success" in result
        assert mock_cli.request.call_count == 2


def test_tavily_search_retries_on_timeout():
    """Test that tavily_search retries on timeout."""
    clear_cache()
    mock_resp_success = MagicMock()
    mock_resp_success.json.return_value = {
        "results": [
            {"title": "Test", "content": "Success", "url": "https://example.com"}
        ]
    }
    mock_resp_success.raise_for_status = MagicMock()

    mock_cli = MagicMock()
    mock_cli.request.side_effect = [
        httpx.TimeoutException("timeout"),
        mock_resp_success,
    ]

    with (
        patch("trending_hunter.llm.tools._get_client", return_value=mock_cli),
        patch("trending_hunter.llm.tools.time.sleep"),
    ):
        result = tavily_search("test", "key")
        assert "Success" in result
        assert mock_cli.request.call_count == 2


def test_tavily_search_retries_on_connect_error():
    """Test that tavily_search retries on connection error."""
    clear_cache()
    mock_resp_success = MagicMock()
    mock_resp_success.json.return_value = {
        "results": [
            {"title": "Test", "content": "Success", "url": "https://example.com"}
        ]
    }
    mock_resp_success.raise_for_status = MagicMock()

    mock_cli = MagicMock()
    mock_cli.request.side_effect = [
        httpx.ConnectError("connection refused"),
        mock_resp_success,
    ]

    with (
        patch("trending_hunter.llm.tools._get_client", return_value=mock_cli),
        patch("trending_hunter.llm.tools.time.sleep"),
    ):
        result = tavily_search("test", "key")
        assert "Success" in result
        assert mock_cli.request.call_count == 2


def test_tavily_search_exhausts_retries():
    """Test that tavily_search raises after max retries exhausted."""
    clear_cache()
    error = httpx.HTTPStatusError(
        "Server Error", request=MagicMock(), response=MagicMock(status_code=500)
    )

    mock_cli = MagicMock()
    mock_cli.request.side_effect = error

    with (
        patch("trending_hunter.llm.tools._get_client", return_value=mock_cli),
        patch("trending_hunter.llm.tools.time.sleep"),
    ):
        with pytest.raises(httpx.HTTPStatusError):
            tavily_search("test", "key")
        assert mock_cli.request.call_count == 3


def test_tavily_extract_retries_on_http_status_error():
    """Test that tavily_extract retries on HTTP status errors."""
    clear_cache()
    mock_resp_success = MagicMock()
    mock_resp_success.json.return_value = {"results": [{"raw_content": "content"}]}
    mock_resp_success.raise_for_status = MagicMock()

    mock_resp_error = MagicMock()
    mock_resp_error.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Rate Limited", request=MagicMock(), response=MagicMock(status_code=429)
    )

    mock_cli = MagicMock()
    mock_cli.request.side_effect = [mock_resp_error, mock_resp_success]

    with (
        patch("trending_hunter.llm.tools._get_client", return_value=mock_cli),
        patch("trending_hunter.llm.tools.time.sleep"),
    ):
        result = tavily_extract("https://example.com", "key")
        assert "content" in result
        assert mock_cli.request.call_count == 2


def test_tavily_extract_exhausts_retries():
    """Test that tavily_extract raises after max retries exhausted."""
    clear_cache()
    error = httpx.ConnectError("connection refused")

    mock_cli = MagicMock()
    mock_cli.request.side_effect = error

    with (
        patch("trending_hunter.llm.tools._get_client", return_value=mock_cli),
        patch("trending_hunter.llm.tools.time.sleep"),
    ):
        with pytest.raises(httpx.ConnectError):
            tavily_extract("https://example.com", "key")
        assert mock_cli.request.call_count == 3


def test_tavily_client_reuse():
    """Test that httpx client is reused as module-level singleton."""
    clear_cache()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {"title": "Test", "content": "content", "url": "https://example.com"}
        ]
    }
    mock_resp.raise_for_status = MagicMock()
    mock_cli = _mock_client(mock_resp)

    with patch("trending_hunter.llm.tools._get_client", return_value=mock_cli):
        tavily_search("query1", "key")
        tavily_search("query2", "key")
        # Two different queries should both make HTTP calls
        assert mock_cli.request.call_count == 2


def test_retry_request_zero_retries():
    """Test that _retry_request with max_retries=0 raises RuntimeError."""
    from trending_hunter.llm.tools import _retry_request

    with pytest.raises(RuntimeError, match="retry called with no attempts"):
        _retry_request("GET", "https://example.com", max_retries=0)


def test_retry_request_zero_retries_non_retryable():
    """max_retries=0 raises RuntimeError, not TypeError."""
    from trending_hunter.llm.tools import _retry_request

    mock_cli = MagicMock()
    mock_cli.request.side_effect = httpx.ConnectError("fail")

    with patch("trending_hunter.llm.tools._get_client", return_value=mock_cli):
        with pytest.raises(RuntimeError, match="retry called with no attempts"):
            _retry_request("GET", "https://example.com", max_retries=0)


def test_get_client_thread_safety():
    """Test that concurrent _get_client calls produce a single client instance."""
    import threading
    import time as _time

    from trending_hunter.llm import tools as tools_mod

    # Reset the module-level singleton
    original_client = tools_mod._client
    tools_mod._client = None

    call_count = 0
    call_lock = threading.Lock()
    barrier = threading.Barrier(10)

    real_client = httpx.Client()

    def slow_counting_client(*args, **kwargs):
        nonlocal call_count
        with call_lock:
            call_count += 1
        _time.sleep(0.01)  # Simulate slow construction to expose race conditions
        return real_client

    try:
        with patch("trending_hunter.llm.tools.httpx.Client", slow_counting_client):

            def worker():
                barrier.wait()  # Force all threads to start concurrently
                tools_mod._get_client()

            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        # Only one Client() should have been constructed thanks to the lock
        assert call_count == 1
        # The module singleton should be set
        assert tools_mod._client is real_client
    finally:
        tools_mod._client = original_client
        real_client.close()
