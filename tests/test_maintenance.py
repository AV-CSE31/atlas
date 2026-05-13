"""Tests for atlas.maintenance — AKL scoring and archive logic."""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from atlas.maintenance import calculate_akl_score


class TestCalculateAklScore:
    def test_fresh_article_full_score(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        score = calculate_akl_score(100, now_iso)
        # Should be very close to 100 (0 days elapsed → e^0 = 1)
        assert score == pytest.approx(100.0, rel=1e-3)

    def test_score_decays_over_time(self) -> None:
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        score = calculate_akl_score(100, old)
        # After 30 days with decay constant 30: score = 100 * e^(-1) ≈ 36.79
        assert score == pytest.approx(100 * math.exp(-1), rel=1e-3)

    def test_zero_importance_always_zero(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        assert calculate_akl_score(0, now_iso) == 0.0

    def test_invalid_timestamp_assumes_zero_days(self) -> None:
        score_invalid = calculate_akl_score(50, "not-a-date")
        score_now = calculate_akl_score(50, datetime.now(timezone.utc).isoformat())
        # Both should be approximately equal (0 days elapsed)
        assert score_invalid == pytest.approx(score_now, rel=1e-2)

    def test_high_importance_higher_score(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        assert calculate_akl_score(80, now_iso) > calculate_akl_score(20, now_iso)
