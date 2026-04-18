from __future__ import annotations

from trending_hunter.llm.client import _parse_sections


def test_parse_sections_normalizes_aliases():
    text = """## Summary
TL;DR content here.

## What and Why
Description here.

## Timing Context
Why now content.

## Technology Wave
Wave content.

## Supply and Demand
S&D content.

## Product Analysis
Product content.

## Creativity & Differentiation
Creative content.

## Competitive Landscape
Competition content.

## Community Signals
Signals content.

## Signal Assessment
Assessment content.

## Open Questions
Questions here."""
    sections = _parse_sections(text)
    assert "TL;DR" in sections
    assert "What & Why" in sections
    assert "Why Now" in sections
    assert "Supply & Demand" in sections
    assert "Summary" not in sections
    assert "What and Why" not in sections
    assert "Timing Context" not in sections
    assert "Supply and Demand" not in sections


def test_parse_sections_preserves_canonical_names():
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
