from __future__ import annotations


_PRICING: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.80 / 1_000_000, 4.00 / 1_000_000),
    "claude-sonnet-4-5-20250514": (3.00 / 1_000_000, 15.00 / 1_000_000),
}

_DEFAULT_PRICING = (3.00 / 1_000_000, 15.00 / 1_000_000)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = _PRICING.get(model, _DEFAULT_PRICING)
    return input_tokens * input_price + output_tokens * output_price


def format_cost_report(token_usage: dict[str, int]) -> str:
    lines: list[str] = []
    total = 0
    for stage, count in token_usage.items():
        lines.append(f"  {stage}: {count} tokens")
        total += count
    lines.append(f"  total: {total} tokens")
    return "\n".join(lines)
