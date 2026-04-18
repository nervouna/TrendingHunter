from __future__ import annotations

from trending_hunter.llm.client import _parse_sections
from trending_hunter.llm.prompts import AUDIT_SYSTEM, DRAFT_SYSTEM, REWRITE_SYSTEM

CANONICAL_HEADERS = [
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
