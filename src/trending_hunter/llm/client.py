from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from typing import TypeVar

import anthropic

from trending_hunter.log import get_logger

_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_T = TypeVar("_T")

log = get_logger()


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


_RETRYABLE = (anthropic.APIConnectionError, anthropic.RateLimitError, anthropic.APITimeoutError)


def _retry_call(fn: Callable[[], _T], max_retries: int = 3) -> _T:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                log.warning("Retry %d/%d after %ds: %s", attempt + 1, max_retries, delay, exc)
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 4096,
        base_url: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        kwargs: dict[str, object] = {"api_key": api_key, "timeout": timeout}
        if base_url:
            base_url = re.sub(r"/v1/messages/?$", "", base_url.rstrip("/"))
            kwargs["base_url"] = base_url
        # Clear env vars that the SDK reads — we pass api_key explicitly
        _prev = {}
        for _k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            if _k in os.environ:
                _prev[_k] = os.environ.pop(_k)
        self._client = anthropic.Anthropic(**kwargs)
        os.environ.update(_prev)
        self._model = model
        self._max_tokens = max_tokens

    def call(self, system: str, user: str) -> tuple[dict[str, str], dict[str, int]]:
        log.info("LLM call: model=%s", self._model)

        def _do_call() -> object:
            return self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )

        response = _retry_call(_do_call)
        text = "".join(
            block.text for block in response.content if hasattr(block, "text")
        )
        sections = _parse_sections(text)
        tokens = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
        log.info("LLM response: model=%s input=%d output=%d", self._model, tokens["input"], tokens["output"])
        return sections, tokens

    def call_with_tools(
        self,
        system: str,
        user: str,
        tools: list[dict],
        tool_handler: Callable[[str, dict], str],
        max_rounds: int = 5,
    ) -> tuple[dict[str, str], dict[str, int]]:
        log.info("LLM call_with_tools: model=%s tools=%s", self._model, [t["name"] for t in tools])

        messages = [{"role": "user", "content": user}]
        total_input = 0
        total_output = 0

        for round_num in range(max_rounds):
            log.debug("Tool round %d/%d", round_num + 1, max_rounds)

            def _do_call() -> object:
                return self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system,
                    messages=messages,
                    tools=tools,
                )

            response = _retry_call(_do_call)
            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

            if response.stop_reason == "end_turn":
                text = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                sections = _parse_sections(text)
                tokens = {"input": total_input, "output": total_output}
                log.info("LLM done: model=%s input=%d output=%d rounds=%d", self._model, total_input, total_output, round_num + 1)
                return sections, tokens

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    log.info("Tool call: %s(%s)", block.name, block.input)
                    result = tool_handler(block.name, block.input)
                    log.debug("Tool result length: %d chars", len(result))
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        log.warning("LLM tool loop exhausted after %d rounds, forcing final response", max_rounds)
        messages.append({"role": "user", "content": "Stop using tools. Write the final report now based on everything you've gathered."})

        def _do_final() -> object:
            return self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=messages,
            )

        final_response = _retry_call(_do_final)
        total_input += final_response.usage.input_tokens
        total_output += final_response.usage.output_tokens

        text = "".join(
            block.text for block in final_response.content if hasattr(block, "text")
        )
        return _parse_sections(text), {"input": total_input, "output": total_output}
