from __future__ import annotations

from trending_hunter.models import TokenUsage
from trending_hunter.settings import ModelPricing


_DEFAULT_PRICING = ModelPricing(input_per_million=3.00, output_per_million=15.00)


def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    pricing: dict[str, ModelPricing] | None = None,
) -> float:
    if pricing and model in pricing:
        p = pricing[model]
    else:
        p = _DEFAULT_PRICING
    return input_tokens * p.input_per_million / 1_000_000 + output_tokens * p.output_per_million / 1_000_000


def format_cost_report(token_usage: dict[str, TokenUsage]) -> str:
    lines: list[str] = []
    total = 0
    for stage, usage in token_usage.items():
        count = usage.input_tokens + usage.output_tokens
        lines.append(f"  {stage}: {count} tokens")
        total += count
    lines.append(f"  total: {total} tokens")
    return "\n".join(lines)
