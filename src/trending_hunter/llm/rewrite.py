from __future__ import annotations

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import REWRITE_SYSTEM, REWRITE_USER


def _sections_to_text(sections: dict[str, str]) -> str:
    parts: list[str] = []
    for name, content in sections.items():
        parts.append(f"## {name}\n{content}")
    return "\n\n".join(parts)


def rewrite_report(
    sections: dict[str, str],
    client: LLMClient,
) -> tuple[dict[str, str], dict[str, int]]:
    user = REWRITE_USER.format(audit_output=_sections_to_text(sections))
    return client.call(REWRITE_SYSTEM, user)
