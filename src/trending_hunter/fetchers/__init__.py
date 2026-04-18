from __future__ import annotations

from datetime import datetime, timezone


def daily_velocity(score: int, posted_at: datetime, now: datetime | None = None) -> float:
    now = now or datetime.now(timezone.utc)
    hours = max((now - posted_at).total_seconds() / 3600, 1)
    return score / hours * 24
