from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from typing import Any, TypeVar, cast

import anthropic
import httpx

from trending_hunter.log import get_logger
from trending_hunter.settings import LLMStageConfig

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


_RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
)


def _retry_call(fn: Callable[[], _T], max_retries: int = 3) -> _T:
    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            return fn()
        except _RETRYABLE as exc:
            last_exc = exc
            if attempt < max_retries - 1:
                delay = 2 ** (attempt + 1)
                log.warning(
                    "Retry %d/%d after %ds: %s", attempt + 1, max_retries, delay, exc
                )
                time.sleep(delay)
    if last_exc is None:
        raise RuntimeError("retry called with no attempts")
    raise last_exc


class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_tokens: int = 4096,
        base_url: str | None = None,
        timeout: float = 120.0,
        max_tool_rounds: int = 5,
    ) -> None:
        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "timeout": timeout,
            "http_client": httpx.Client(trust_env=False, timeout=timeout),
        }
        if base_url:
            base_url = re.sub(r"/v1/messages/?$", "", base_url.rstrip("/"))
            kwargs["base_url"] = base_url
        # Clear env vars that the SDK reads — we pass api_key explicitly
        _prev: dict[str, str] = {}
        for _k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"):
            if _k in os.environ:
                _prev[_k] = os.environ.pop(_k)
        try:
            self._client = anthropic.Anthropic(**kwargs)
        finally:
            os.environ.update(_prev)
        self._model = model
        self._max_tokens = max_tokens
        self._max_tool_rounds = max_tool_rounds

    @classmethod
    def from_stage_config(cls, cfg: LLMStageConfig) -> LLMClient:
        return cls(
            api_key=cfg.api_key,
            model=cfg.model,
            max_tokens=cfg.max_tokens,
            base_url=cfg.base_url or None,
            timeout=cfg.timeout,
            max_tool_rounds=cfg.max_tool_rounds,
        )

    def call(self, system: str, user: str) -> tuple[dict[str, str], dict[str, int]]:
        log.info("LLM call: model=%s", self._model)

        def _do_call() -> Any:
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
        if not text.strip():
            raise ValueError(f"LLM returned empty content (model={self._model})")
        sections = _parse_sections(text)
        tokens = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }
        log.info(
            "LLM response: model=%s input=%d output=%d",
            self._model,
            tokens["input"],
            tokens["output"],
        )
        return sections, tokens

    def call_with_tools(
        self,
        system: str,
        user: str,
        tools: list[dict[str, Any]],
        tool_handler: Callable[[str, dict[str, Any]], str],
        max_rounds: int | None = None,
    ) -> tuple[dict[str, str], dict[str, int]]:
        effective_rounds = (
            max_rounds if max_rounds is not None else self._max_tool_rounds
        )
        log.info(
            "LLM call_with_tools: model=%s tools=%s",
            self._model,
            [t["name"] for t in tools],
        )

        messages: list[Any] = [{"role": "user", "content": user}]
        total_input = 0
        total_output = 0

        for round_num in range(effective_rounds):
            log.debug("Tool round %d/%d", round_num + 1, effective_rounds)

            def _do_call() -> Any:
                return self._client.messages.create(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system,
                    messages=messages,
                    tools=cast(Any, tools),
                )

            response = _retry_call(_do_call)
            total_input += response.usage.input_tokens
            total_output += response.usage.output_tokens

            if response.stop_reason == "end_turn":
                text = "".join(
                    block.text for block in response.content if hasattr(block, "text")
                )
                if not text.strip():
                    raise ValueError(
                        f"LLM returned empty content (model={self._model})"
                    )
                sections = _parse_sections(text)
                tokens = {"input": total_input, "output": total_output}
                log.info(
                    "LLM done: model=%s input=%d output=%d rounds=%d",
                    self._model,
                    total_input,
                    total_output,
                    round_num + 1,
                )
                return sections, tokens

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    log.info("Tool call: %s(%s)", block.name, block.input)
                    result = tool_handler(block.name, block.input)
                    log.debug("Tool result length: %d chars", len(result))
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

        log.warning(
            "LLM tool loop exhausted after %d rounds, forcing final response",
            effective_rounds,
        )
        messages.append(
            {
                "role": "user",
                "content": (
                    "Stop using tools. Write the final report now based on "
                    "everything you've gathered."
                ),
            }
        )

        def _do_final() -> Any:
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
        if not text.strip():
            raise ValueError(f"LLM returned empty content (model={self._model})")
        return _parse_sections(text), {"input": total_input, "output": total_output}
