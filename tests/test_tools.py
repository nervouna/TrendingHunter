from unittest.mock import patch, MagicMock

from trending_hunter.llm.tools import tavily_search, tavily_extract, _clear_cache


def test_tavily_search_returns_text():
    _clear_cache()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {"title": "Test", "content": "A test result.", "url": "https://example.com"},
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("trending_hunter.llm.tools.httpx.post", return_value=mock_resp) as mock_post:
        result = tavily_search("test query", "fake-key")
        assert "Test" in result
        assert "A test result" in result
        assert mock_post.call_count == 1

        # second call should use cache
        result2 = tavily_search("test query", "fake-key")
        assert result2 == result
        assert mock_post.call_count == 1


def test_tavily_extract_returns_content():
    _clear_cache()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [{"raw_content": "# README\nHello world."}]
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("trending_hunter.llm.tools.httpx.post", return_value=mock_resp) as mock_post:
        result = tavily_extract("https://github.com/x/y", "fake-key")
        assert "README" in result
        assert mock_post.call_count == 1

        # cache hit
        tavily_extract("https://github.com/x/y", "fake-key")
        assert mock_post.call_count == 1


def test_tavily_extract_different_urls_not_cached():
    _clear_cache()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [{"raw_content": "content"}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("trending_hunter.llm.tools.httpx.post", return_value=mock_resp) as mock_post:
        tavily_extract("https://a.com", "key")
        tavily_extract("https://b.com", "key")
        assert mock_post.call_count == 2
