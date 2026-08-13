"""Tests unitaires — sélecteurs de coupons."""

import pytest

from app.config.settings import Settings
from app.coupons.selectors import combined_odds, select_free, select_high_odds, select_safe, select_value
from app.database.enums import ConfidenceLevel, CouponType, RiskDecision
from tests.fixtures.coupon_helpers import make_candidate, make_high_odds_pool, make_safe_pool, make_value_pool


class TestCouponSelectors:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            coupon_safe_min_selections=3,
            coupon_safe_max_selections=5,
            coupon_safe_min_probability=0.55,
            coupon_safe_max_odds=2.0,
            coupon_value_min_selections=2,
            coupon_value_max_selections=5,
            value_edge_min_threshold=0.05,
            coupon_high_odds_min_selections=4,
            coupon_high_odds_min_combined=15.0,
            coupon_free_min_selections=3,
            coupon_free_max_selections=4,
            coupon_free_min_probability=0.50,
        )

    def test_combined_odds(self):
        candidates = make_safe_pool(3)
        assert combined_odds(candidates) == pytest.approx(
            candidates[0].decimal_odds * candidates[1].decimal_odds * candidates[2].decimal_odds
        )

    def test_select_safe_success(self, settings):
        result = select_safe(make_safe_pool(4), settings)
        assert not result.skipped
        assert result.coupon_type == CouponType.SAFE
        assert 3 <= len(result.candidates) <= 5

    def test_select_safe_skipped(self, settings):
        pool = make_safe_pool(2)
        result = select_safe(pool, settings)
        assert result.skipped
        assert len(result.candidates) == 0

    def test_select_safe_rejects_low_confidence(self, settings):
        pool = [
            make_candidate(i, confidence=ConfidenceLevel.MEDIUM)
            for i in range(1, 6)
        ]
        result = select_safe(pool, settings)
        assert result.skipped

    def test_select_value_success(self, settings):
        result = select_value(make_value_pool(3), settings)
        assert not result.skipped
        assert result.coupon_type == CouponType.VALUE
        assert len(result.candidates) >= 2

    def test_select_value_skipped(self, settings):
        pool = [make_candidate(1, is_value=True, value_edge=0.02)]
        result = select_value(pool, settings)
        assert result.skipped

    def test_select_high_odds_success(self, settings):
        result = select_high_odds(make_high_odds_pool(4), settings)
        assert not result.skipped
        assert result.total_odds >= settings.coupon_high_odds_min_combined

    def test_select_high_odds_combined_too_low(self, settings):
        settings.coupon_high_odds_min_odds = 1.5
        pool = [
            make_candidate(i, decimal_odds=1.6, probability=0.35)
            for i in range(1, 5)
        ]
        result = select_high_odds(pool, settings)
        assert result.skipped
        assert result.total_odds < settings.coupon_high_odds_min_combined

    def test_select_free_success(self, settings):
        pool = make_safe_pool(4)
        result = select_free(pool, settings)
        assert not result.skipped
        assert result.coupon_type == CouponType.FREE
        assert len(result.candidates) >= 3

    def test_select_free_excludes_premium_keys(self, settings):
        pool = make_safe_pool(4)
        exclude = {pool[0].candidate_key}
        result = select_free(pool, settings, exclude_keys=exclude)
        assert all(c.candidate_key not in exclude for c in result.candidates)

    def test_dedupe_one_selection_per_match(self, settings):
        pool = [
            make_candidate(1, selection="HOME", probability=0.70),
            make_candidate(1, selection="DRAW", probability=0.65),
            *make_safe_pool(3, start_id=2),
        ]
        result = select_safe(pool, settings)
        match_ids = [c.match_id for c in result.candidates]
        assert len(match_ids) == len(set(match_ids))

    def test_reject_not_publishable(self, settings):
        pool = [
            make_candidate(i, risk_decision=RiskDecision.REJECT)
            for i in range(1, 6)
        ]
        assert select_safe(pool, settings).skipped
        assert select_value(pool, settings).skipped
        assert select_free(pool, settings).skipped
