from unittest.mock import MagicMock, patch

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.draft import generate_draft
from trending_hunter.llm.audit import audit_report
from trending_hunter.llm.rewrite import rewrite_report
from trending_hunter.models import Project, Source


def _sample_project() -> Project:
    return Project(
        name="owner/repo",
        source=Source.GITHUB,
        url="https://github.com/owner/repo",
        stars=500,
        star_velocity=50.0,
        repo_age_days=30,
        description="A cool project",
        readme_excerpt="# Repo\nThis does cool things.",
    )


SECTION_NAMES = [
    "TL;DR",
    "What & Why",
    "Why Now",
    "Technology Wave",
    "Supply & Demand",
    "Product Analysis",
    "Creativity & Differentiation",
    "Competitive Landscape",
    "Community Signals",
    "Signal Assessment",
    "Open Questions",
]


def _mock_sections() -> dict[str, str]:
    return {name: f"Content for {name}." for name in SECTION_NAMES}


def test_generate_draft_returns_sections():
    client = MagicMock(spec=LLMClient)
    client.call.return_value = (_mock_sections(), {"input": 100, "output": 200})

    with patch("trending_hunter.llm.draft.tavily_extract", return_value="content"), \
         patch("trending_hunter.llm.draft.tavily_search", return_value="search results"):
        sections, tokens = generate_draft(_sample_project(), client, tavily_key="fake")

    assert set(sections.keys()) == set(SECTION_NAMES)
    assert tokens["input"] == 100
    assert tokens["output"] == 200
    client.call.assert_called_once()


def test_generate_draft_without_tavily():
    client = MagicMock(spec=LLMClient)
    client.call.return_value = (_mock_sections(), {"input": 100, "output": 200})

    sections, tokens = generate_draft(_sample_project(), client)

    assert set(sections.keys()) == set(SECTION_NAMES)
    client.call.assert_called_once()


def test_audit_report_returns_sections():
    client = MagicMock(spec=LLMClient)
    draft = _mock_sections()
    client.call_with_tools.return_value = (_mock_sections(), {"input": 150, "output": 250})

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
            api_key="k", model="m",
            base_url="https://example.com/v1/messages/",
        )
        client.call("sys", "usr")

    call_kwargs = mock_cls.call_args[1]
    assert call_kwargs["base_url"] == "https://example.com"


def test_llm_client_clears_env_vars():
    import os
    os.environ["ANTHROPIC_API_KEY"] = "env-key"
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## TL;DR\nTest.")]
    mock_response.usage.input_tokens = 10
    mock_response.usage.output_tokens = 20

    try:
        with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            client = LLMClient(api_key="explicit-key", model="m")
            client.call("sys", "usr")
        assert os.environ["ANTHROPIC_API_KEY"] == "env-key"
    finally:
        pass


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
        mock_cls.return_value.messages.create.side_effect = [mock_response_tool, mock_response_final]

        client = LLMClient(api_key="k", model="m")
        handler = MagicMock(return_value="search results")
        sections, tokens = client.call_with_tools(
            "sys", "usr",
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
        mock_cls.return_value.messages.create.side_effect = [mock_response, mock_response, mock_final]

        client = LLMClient(api_key="k", model="m")
        handler = MagicMock(return_value="result")
        sections, tokens = client.call_with_tools(
            "sys", "usr",
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


def test_audit_make_tool_handler_unknown():
    from trending_hunter.llm.audit import _make_tool_handler
    handler = _make_tool_handler("fake-key")
    result = handler("unknown_tool", {"foo": "bar"})
    assert "Unknown tool" in result


def test_audit_make_tool_handler_search():
    from trending_hunter.llm.audit import _make_tool_handler
    with patch("trending_hunter.llm.audit.tavily_search", return_value="search results") as mock_search:
        handler = _make_tool_handler("fake-key")
        result = handler("tavily_search", {"query": "test"})
        assert result == "search results"
        mock_search.assert_called_once_with("test", "fake-key")


def test_audit_make_tool_handler_extract():
    from trending_hunter.llm.audit import _make_tool_handler
    with patch("trending_hunter.llm.audit.tavily_extract", return_value="extracted") as mock_extract:
        handler = _make_tool_handler("fake-key")
        result = handler("tavily_extract", {"url": "https://example.com"})
        assert result == "extracted"
        mock_extract.assert_called_once_with("https://example.com", "fake-key")


def test_get_language_modifier():
    from trending_hunter.llm.prompts import get_language_modifier
    assert get_language_modifier("chinese") == "\n\nWrite the entire report in chinese. Section headers must also be translated."
    assert get_language_modifier("") == ""
