from unittest.mock import MagicMock, patch

import anthropic
import pytest

from tests.conftest import (
    SECTION_NAMES,
    _mock_sections,
)
from tests.conftest import (
    _make_project as _sample_project,
)
from trending_hunter.llm.audit import audit_report
from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.draft import generate_draft
from trending_hunter.llm.rewrite import rewrite_report


def test_generate_draft_returns_sections():
    client = MagicMock(spec=LLMClient)
    client.call.return_value = (_mock_sections(), {"input": 100, "output": 200})

    with (
        patch(
            "trending_hunter.llm.draft.tavily_extract", return_value="content"
        ) as mock_extract,
        patch(
            "trending_hunter.llm.draft.tavily_search", return_value="search results"
        ) as mock_search,
    ):
        sections, tokens = generate_draft(_sample_project(), client, tavily_key="fake")

    assert set(sections.keys()) == set(SECTION_NAMES)
    assert tokens["input"] == 100
    assert tokens["output"] == 200
    client.call.assert_called_once()
    mock_extract.assert_called_once()
    mock_search.assert_called_once()


def test_generate_draft_calls_tavily_in_parallel():
    """Test that tavily_extract and tavily_search are called concurrently."""
    import threading
    import time as _time

    client = MagicMock(spec=LLMClient)
    client.call.return_value = (_mock_sections(), {"input": 100, "output": 200})

    extract_threads: list[int] = []
    search_threads: list[int] = []

    def mock_extract(*args, **kwargs):
        _time.sleep(0.05)
        extract_threads.append(threading.current_thread().ident or 0)
        return "content"

    def mock_search(*args, **kwargs):
        _time.sleep(0.05)
        search_threads.append(threading.current_thread().ident or 0)
        return "search results"

    with (
        patch("trending_hunter.llm.draft.tavily_extract", side_effect=mock_extract),
        patch("trending_hunter.llm.draft.tavily_search", side_effect=mock_search),
    ):
        generate_draft(_sample_project(), client, tavily_key="fake")

    assert len(extract_threads) == 1
    assert len(search_threads) == 1
    assert extract_threads[0] != search_threads[0]


def test_generate_draft_without_tavily():
    client = MagicMock(spec=LLMClient)
    client.call.return_value = (_mock_sections(), {"input": 100, "output": 200})

    sections, tokens = generate_draft(_sample_project(), client)

    assert set(sections.keys()) == set(SECTION_NAMES)
    client.call.assert_called_once()


def test_audit_report_returns_sections():
    client = MagicMock(spec=LLMClient)
    draft = _mock_sections()
    client.call_with_tools.return_value = (
        _mock_sections(),
        {"input": 150, "output": 250},
    )

    sections, tokens = audit_report(draft, _sample_project(), client, tavily_key="fake")

    assert set(sections.keys()) == set(SECTION_NAMES)
    assert tokens["input"] == 150
    client.call_with_tools.assert_called_once()


def test_llm_client_calls_anthropic():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## TL;DR\nTest.")]
    mock_response.usage.input_tokens = 50
    mock_response.usage.output_tokens = 100
    mock_response.stop_reason = "end_turn"

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response

        client = LLMClient(api_key="test-key", model="claude-test", max_tokens=1000)
        sections, tokens = client.call("system prompt", "user prompt")

    assert "TL;DR" in sections
    assert tokens["input"] == 50
    assert tokens["output"] == 100
    mock_cls.return_value.messages.create.assert_called_once()


def test_rewrite_report_returns_sections():
    client = MagicMock(spec=LLMClient)
    client.call.return_value = (_mock_sections(), {"input": 80, "output": 150})

    annotated = {name: f"**Correction:** Content for {name}." for name in SECTION_NAMES}
    sections, tokens = rewrite_report(annotated, client)

    assert set(sections.keys()) == set(SECTION_NAMES)
    assert tokens["input"] == 80
    client.call.assert_called_once()


def test_llm_client_strips_base_url():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## TL;DR\nTest.")]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 20

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        client = LLMClient(
            api_key="k",
            model="m",
            base_url="https://example.com/v1/messages/",
        )
        client.call("sys", "usr")

    call_kwargs = mock_cls.call_args[1]
    assert call_kwargs["base_url"] == "https://example.com"


def test_llm_client_clears_env_vars(monkeypatch):
    import os

    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## TL;DR\nTest.")]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 20

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        client = LLMClient(api_key="explicit-key", model="m")
        client.call("sys", "usr")
    assert os.environ["ANTHROPIC_API_KEY"] == "env-key"


def test_call_with_tools_tool_use_round():
    mock_response_tool = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "tavily_search"
    tool_block.input = {"query": "test"}
    tool_block.id = "tool-1"
    mock_response_tool.content = [tool_block]
    mock_response_tool.stop_reason = "tool_use"
    mock_response_tool.usage.input_tokens = 50
    mock_response_tool.usage.output_tokens = 30

    mock_response_final = MagicMock()
    mock_response_final.content = [MagicMock(text="## TL;DR\nDone.")]
    mock_response_final.stop_reason = "end_turn"
    mock_response_final.usage.input_tokens = 40
    mock_response_final.usage.output_tokens = 20

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = [
            mock_response_tool,
            mock_response_final,
        ]

        client = LLMClient(api_key="k", model="m")
        handler = MagicMock(return_value="search results")
        sections, tokens = client.call_with_tools(
            "sys",
            "usr",
            tools=[{"name": "tavily_search", "input_schema": {}}],
            tool_handler=handler,
        )

    assert "TL;DR" in sections
    assert tokens["input"] == 90
    assert tokens["output"] == 50
    handler.assert_called_once_with("tavily_search", {"query": "test"})


def test_call_with_tools_max_rounds_exhausted():
    mock_response = MagicMock()
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "tavily_search"
    tool_block.input = {"query": "test"}
    tool_block.id = "tool-1"
    mock_response.content = [tool_block]
    mock_response.stop_reason = "tool_use"
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    mock_final = MagicMock()
    mock_final.content = [MagicMock(text="## TL;DR\nFinal.")]
    mock_final.usage.input_tokens = 20
    mock_final.usage.output_tokens = 10

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.side_effect = [
            mock_response,
            mock_response,
            mock_final,
        ]

        client = LLMClient(api_key="k", model="m")
        handler = MagicMock(return_value="result")
        sections, tokens = client.call_with_tools(
            "sys",
            "usr",
            tools=[{"name": "tavily_search", "input_schema": {}}],
            tool_handler=handler,
            max_rounds=2,
        )

    assert "TL;DR" in sections
    assert handler.call_count == 2


def test_audit_report_without_tavily():
    client = MagicMock(spec=LLMClient)
    client.call.return_value = (_mock_sections(), {"input": 100, "output": 200})

    draft = _mock_sections()
    sections, tokens = audit_report(draft, _sample_project(), client)

    assert set(sections.keys()) == set(SECTION_NAMES)
    client.call.assert_called_once()
    client.call_with_tools.assert_not_called()


def test_generate_draft_cancels_search_future_on_extract_failure():
    """Test that search_future is cancelled when extract_future fails."""
    client = MagicMock(spec=LLMClient)

    def failing_extract(*args, **kwargs):
        raise RuntimeError("extract failed")

    mock_search = MagicMock(return_value="search results")

    with (
        patch("trending_hunter.llm.draft.tavily_extract", side_effect=failing_extract),
        patch("trending_hunter.llm.draft.tavily_search", side_effect=mock_search),
    ):
        with pytest.raises(RuntimeError, match="extract failed"):
            generate_draft(_sample_project(), client, tavily_key="fake")

    # search should not have been called (cancelled before completion)
    mock_search.assert_not_called()


def test_audit_make_tool_handler_unknown():
    from trending_hunter.llm.audit import _make_tool_handler

    handler = _make_tool_handler("fake-key")
    result = handler("unknown_tool", {"foo": "bar"})
    assert "Unknown tool" in result


def test_audit_make_tool_handler_search():
    from trending_hunter.llm.audit import _make_tool_handler

    with patch(
        "trending_hunter.llm.audit.tavily_search", return_value="search results"
    ) as mock_search:
        handler = _make_tool_handler("fake-key")
        result = handler("tavily_search", {"query": "test"})
        assert result == "search results"
        mock_search.assert_called_once_with("test", "fake-key")


def test_audit_make_tool_handler_extract():
    from trending_hunter.llm.audit import _make_tool_handler

    with patch(
        "trending_hunter.llm.audit.tavily_extract", return_value="extracted"
    ) as mock_extract:
        handler = _make_tool_handler("fake-key")
        result = handler("tavily_extract", {"url": "https://example.com"})
        assert result == "extracted"
        mock_extract.assert_called_once_with("https://example.com", "fake-key")


def test_get_language_modifier():
    from trending_hunter.llm.prompts import get_language_modifier

    expected = (
        "\n\nWrite the entire report in chinese. "
        "Section headers must also be translated."
    )
    assert get_language_modifier("chinese") == expected
    assert get_language_modifier("") == ""


# --- _retry_call tests ---


def test_retry_call_succeeds_after_transient_failure():
    from trending_hunter.llm.client import _retry_call

    call_count = 0

    def flaky_fn():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise anthropic.APIConnectionError(request=MagicMock())
        return "ok"

    with patch("trending_hunter.llm.client.time.sleep"):
        result = _retry_call(flaky_fn, max_retries=3)

    assert result == "ok"
    assert call_count == 2


def test_retry_call_raises_after_max_retries():
    from trending_hunter.llm.client import _retry_call

    def always_fail():
        raise anthropic.RateLimitError(
            response=MagicMock(status_code=429, headers={}),
            message="rate limited",
            body=None,
        )

    with patch("trending_hunter.llm.client.time.sleep"):
        with pytest.raises(anthropic.RateLimitError):
            _retry_call(always_fail, max_retries=3)


def test_retry_call_no_retry_on_non_retryable():
    from trending_hunter.llm.client import _retry_call

    call_count = 0

    def non_retryable():
        nonlocal call_count
        call_count += 1
        raise anthropic.BadRequestError(
            response=MagicMock(status_code=400, headers={}),
            message="bad request",
            body=None,
        )

    with pytest.raises(anthropic.BadRequestError):
        _retry_call(non_retryable, max_retries=3)

    assert call_count == 1


def test_retry_call_zero_retries():
    """Test that _retry_call with max_retries=0 raises RuntimeError."""
    from trending_hunter.llm.client import _retry_call

    with pytest.raises(RuntimeError, match="retry called with no attempts"):
        _retry_call(lambda: "ok", max_retries=0)


def test_retry_call_zero_retries_on_exception():
    """Test that _retry_call with max_retries=0 raises RuntimeError, not TypeError."""
    from trending_hunter.llm.client import _retry_call

    def always_fail():
        raise anthropic.APIConnectionError(request=MagicMock())

    with pytest.raises(RuntimeError, match="retry called with no attempts"):
        _retry_call(always_fail, max_retries=0)


# --- empty content ValueError tests ---


def test_call_raises_on_empty_content():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(spec=[])]  # no .text attr
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        client = LLMClient(api_key="k", model="m")

        with pytest.raises(ValueError, match="empty"):
            client.call("sys", "usr")


def test_call_with_tools_raises_on_empty_content():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(spec=[])]  # no .text attr
    mock_response.stop_reason = "end_turn"
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 5

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response
        client = LLMClient(api_key="k", model="m")

        with pytest.raises(ValueError, match="empty"):
            client.call_with_tools("sys", "usr", tools=[], tool_handler=MagicMock())
