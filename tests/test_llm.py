from unittest.mock import MagicMock, patch

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.draft import generate_draft
from trending_hunter.llm.audit import audit_report
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

    sections, tokens = generate_draft(_sample_project(), client)

    assert set(sections.keys()) == set(SECTION_NAMES)
    assert tokens["input"] == 100
    assert tokens["output"] == 200
    client.call.assert_called_once()


def test_audit_report_returns_sections():
    client = MagicMock(spec=LLMClient)
    draft = _mock_sections()
    client.call.return_value = (_mock_sections(), {"input": 150, "output": 250})

    sections, tokens = audit_report(draft, _sample_project(), client)

    assert set(sections.keys()) == set(SECTION_NAMES)
    assert tokens["input"] == 150
    client.call.assert_called_once()


def test_llm_client_calls_anthropic():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="## TL;DR\nTest.")]
    mock_response.usage.input_tokens = 50
    mock_response.usage.output_tokens = 100

    with patch("trending_hunter.llm.client.anthropic.Anthropic") as mock_cls:
        mock_cls.return_value.messages.create.return_value = mock_response

        client = LLMClient(api_key="test-key", model="claude-test", max_tokens=1000)
        sections, tokens = client.call("system prompt", "user prompt")

    assert "TL;DR" in sections
    assert tokens["input"] == 50
    assert tokens["output"] == 100
    mock_cls.return_value.messages.create.assert_called_once()
