from __future__ import annotations

from unittest.mock import MagicMock, patch

from trending_hunter.llm.client import LLMClient, _parse_sections
from trending_hunter.llm.prompts import AUDIT_SYSTEM, DRAFT_SYSTEM, REWRITE_SYSTEM
from trending_hunter.settings import LLMStageConfig

CANONICAL_HEADERS = [
    "TL;DR",
    "Product & Design",
    "Market & Business",
    "Technology & Architecture",
    "Competitive Edge & Verdict",
]


def test_all_prompts_list_canonical_headers():
    for header in CANONICAL_HEADERS:
        assert header in DRAFT_SYSTEM, f"DRAFT_SYSTEM missing '{header}'"
        assert header in REWRITE_SYSTEM, f"REWRITE_SYSTEM missing '{header}'"


def test_parse_sections_preserves_exact_names():
    text = """## TL;DR
Content.

## What & Why
More content."""
    sections = _parse_sections(text)
    assert "TL;DR" in sections
    assert "What & Why" in sections


def test_parse_sections_fallback_for_unknown():
    text = """## Unknown Section
Content."""
    sections = _parse_sections(text)
    assert "Unknown Section" in sections


def test_parse_sections_no_headers():
    text = "Just plain text with no section headers."
    sections = _parse_sections(text)
    assert sections == {"TL;DR": "Just plain text with no section headers."}


def test_from_stage_config():
    cfg = LLMStageConfig(
        base_url="https://example.com/v1/messages/",
        api_key="test-key",
        model="claude-test",
        max_tokens=2048,
        timeout=60.0,
    )
    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        client = LLMClient.from_stage_config(cfg)

    assert client._model == "claude-test"
    assert client._max_tokens == 2048
    call_kwargs = mock_cls.call_args[1]
    assert call_kwargs["api_key"] == "test-key"
    assert call_kwargs["base_url"] == "https://example.com"
    assert call_kwargs["timeout"] == 60.0


def test_from_stage_config_empty_base_url():
    cfg = LLMStageConfig(api_key="k", model="m")
    with patch("trending_hunter.llm.client.anthropic.Anthropic"):
        client = LLMClient.from_stage_config(cfg)

    assert client._model == "m"


def test_llmclient_passes_trust_env_false_to_httpx():
    with patch("trending_hunter.llm.client.httpx.Client") as mock_httpx, \
         patch("trending_hunter.llm.client.anthropic.Anthropic"):
        LLMClient(api_key="k", model="m", timeout=30.0)
    assert mock_httpx.call_args.kwargs["trust_env"] is False
    assert mock_httpx.call_args.kwargs["timeout"] == 30.0
