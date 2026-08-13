"""Fixtures partagées — tests d'intégration."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.config.settings import Settings
from app.repositories.odds_repository import OddsRepository
from app.value.odds_normalizer import normalize_odds_event
from tests.fixtures.feature_helpers import seed_feature_test_data
from tests.fixtures.odds_helpers import ODDS_API_EVENT


@pytest.fixture
def integration_settings() -> Settings:
    """Settings permissifs pour enchaîner plusieurs modules sans API externe."""
    return Settings(
        _env_file=None,
        timezone="UTC",
        value_edge_min_threshold=0.03,
        coupon_safe_min_selections=1,
        coupon_value_min_selections=1,
        coupon_high_odds_min_selections=2,
        coupon_high_odds_min_combined=3.0,
        coupon_free_min_selections=1,
        coupon_safe_max_selections=4,
        coupon_value_max_selections=4,
        coupon_high_odds_max_selections=4,
        coupon_safe_min_probability=0.5,
        coupon_safe_max_odds=8.0,
        coupon_free_min_probability=0.45,
        risk_check_injuries=False,
        risk_check_lineups=False,
        risk_reject_stale_data=False,
        calibration_enable=False,
        prediction_enable_ml=False,
        prediction_enable_dixon_coles=True,
        prediction_min_matches=3,
        feature_min_matches=3,
        feature_form_window=5,
        publication_enable=True,
        publication_confirm_if_unchanged=True,
        telegram_bot_token="123456:TEST",
        telegram_free_channel_id="@freechannel",
        telegram_premium_group_id="@premiumgroup",
        backtest_min_matches=3,
        tracking_settle_days_back=30,
    )


@pytest.fixture
def seeded_match_day(db_session, integration_settings) -> dict:
    """
    Match du 2026-08-20 avec historique features + cotes Odds API normalisées.
    """
    data = seed_feature_test_data(db_session)
    match = data["target_match"]
    match.scheduled_at = datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc)
    db_session.flush()

    normalized = normalize_odds_event(ODDS_API_EVENT)
    OddsRepository(db_session).store_normalized_odds(match.id, normalized)

    return {
        **data,
        "target_date": date(2026, 8, 20),
        "match": match,
    }
