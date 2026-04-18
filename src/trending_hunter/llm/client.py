from __future__ import annotations

import re

import anthropic

_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def _parse_sections(text: str) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        return {"TL;DR": text.strip()}

    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[name] = text[start:end].strip()
    return sections


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 4096,
        base_url: str | None = None,
    ) -> None:
        kwargs: dict[str, object] = {"api_key": api_key}
        if base_url:
            base_url = re.sub(r"/v1/messages/?$", "", base_url.rstrip("/"))
            kwargs["base_url"] = base_url
        self._client = anthropic.Anthropic(**kwargs)
        self._model = model
        self._max_tokens = max_tokens

    def call(self, system: str, user: str) -> tuple[dict[str, str], dict[str, int]]:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        sections = _parse_sections(text)
        tokens = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
        return sections, tokens
