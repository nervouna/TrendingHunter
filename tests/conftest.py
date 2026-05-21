from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from trending_hunter.models import Project, Source

SECTION_NAMES = [
    "TL;DR",
    "Product & Design",
    "Market & Business",
    "Technology & Architecture",
    "Competitive Edge & Verdict",
]


def _make_project(name: str = "owner/repo") -> Project:
    return Project(
        name=name,
        source=Source.GITHUB,
        url=f"https://github.com/{name}",
        stars=500,
        star_velocity=50.0,
        repo_age_days=30,
        description="A cool project",
        readme_excerpt="# Repo\nThis does cool things.",
    )


def _mock_sections() -> dict[str, str]:
    return {name: f"Content for {name}." for name in SECTION_NAMES}


@pytest.fixture
def patched_fetchers() -> dict[str, MagicMock]:
    """Provide _FETCHERS for in-place mutation, then restore it."""
    import trending_hunter.cli as cli_mod

    original = dict(cli_mod._FETCHERS)
    yield cli_mod._FETCHERS
    cli_mod._FETCHERS.clear()
    cli_mod._FETCHERS.update(original)
