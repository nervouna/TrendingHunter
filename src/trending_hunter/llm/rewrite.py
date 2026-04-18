from __future__ import annotations

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import REWRITE_SYSTEM, REWRITE_USER, get_language_modifier
from trending_hunter.writer import sections_to_text


def rewrite_report(
    sections: dict[str, str],
    client: LLMClient,
    language: str = "",
) -> tuple[dict[str, str], dict[str, int]]:
    user = REWRITE_USER.format(audit_output=sections_to_text(sections))
    system = REWRITE_SYSTEM + get_language_modifier(language)
    return client.call(system, user)
