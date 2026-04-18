from __future__ import annotations

from trending_hunter.llm.client import LLMClient
from trending_hunter.llm.prompts import REWRITE_SYSTEM, REWRITE_USER
from trending_hunter.writer import sections_to_text


def rewrite_report(
    sections: dict[str, str],
    client: LLMClient,
) -> tuple[dict[str, str], dict[str, int]]:
    user = REWRITE_USER.format(audit_output=sections_to_text(sections))
    return client.call(REWRITE_SYSTEM, user)
