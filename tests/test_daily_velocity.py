from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trending_hunter.fetchers import daily_velocity


def test_basic_velocity():
    now = datetime(2026, 4, 20, 8, 0, 0, tzinfo=timezone.utc)
    posted = now - timedelta(hours=24)
    assert daily_velocity(score=24, posted_at=posted, now=now) == 24.0


def test_min_hours_protection():
    now = datetime(2026, 4, 20, 8, 0, 0, tzinfo=timezone.utc)
    posted = now - timedelta(seconds=10)
    result = daily_velocity(score=100, posted_at=posted, now=now)
    assert result == 100.0 / 1 * 24


def test_explicit_now_parameter():
    posted = datetime(2026, 4, 18, 8, 0, 0, tzinfo=timezone.utc)
    now = datetime(2026, 4, 20, 8, 0, 0, tzinfo=timezone.utc)
    result = daily_velocity(score=48, posted_at=posted, now=now)
    assert result == 24.0


def test_fractional_hours():
    now = datetime(2026, 4, 20, 8, 0, 0, tzinfo=timezone.utc)
    posted = now - timedelta(hours=12)
    result = daily_velocity(score=12, posted_at=posted, now=now)
    assert result == 24.0


def test_score_zero():
    now = datetime(2026, 4, 20, 8, 0, 0, tzinfo=timezone.utc)
    posted = now - timedelta(hours=24)
    assert daily_velocity(score=0, posted_at=posted, now=now) == 0.0


def test_timezone_naive_posted_at():
    now = datetime(2026, 4, 20, 8, 0, 0, tzinfo=timezone.utc)
    posted = datetime(2026, 4, 18, 8, 0, 0)
    with pytest.raises(TypeError):
        daily_velocity(score=100, posted_at=posted, now=now)
