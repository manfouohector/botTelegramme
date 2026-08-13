"""Tests unitaires — formatters publication."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.config.settings import Settings
from app.coupons.schemas import GeneratedCoupon
from app.database.enums import ConfidenceLevel, CouponStatus, CouponType, RiskDecision
from app.models.coupon import Coupon, CouponPrediction
from app.models.prediction import Prediction
from app.publication.constants import CONFIRMATION_MESSAGE
from app.publication.formatters import (
    format_confirmation_message,
    format_coupon_message,
    format_generated_coupon_preview,
    format_selection_label,
)
from tests.fixtures.coupon_helpers import make_safe_pool


@pytest.fixture
def pub_settings():
    return Settings(_env_file=None, app_name="Test Bot", timezone="UTC")


class TestPublicationFormatters:
    def test_selection_labels(self):
        assert format_selection_label("1X2", "HOME") == "1"
        assert format_selection_label("1X2", "DRAW") == "N"
        assert format_selection_label("BTTS", "YES") == "Oui"
        assert format_selection_label("OU25", "UNDER") == "-2.5 buts"

    def test_format_generated_free_preview(self, pub_settings):
        generated = GeneratedCoupon(
            coupon_type=CouponType.FREE,
            candidates=make_safe_pool(3),
            total_odds=4.5,
        )
        text = format_generated_coupon_preview(generated, pub_settings, detailed=False)
        assert "COUPON GRATUIT" in text
        assert "Cote combinée" in text
        assert "Test Bot" in text

    def test_format_generated_premium_detailed(self, pub_settings):
        generated = GeneratedCoupon(
            coupon_type=CouponType.SAFE,
            candidates=make_safe_pool(2),
            total_odds=3.2,
        )
        text = format_generated_coupon_preview(generated, pub_settings, detailed=True)
        assert "COUPON SAFE" in text
        assert "Probabilité" in text
        assert "Confiance" in text

    def test_format_confirmation_message(self):
        text = format_confirmation_message(CouponType.SAFE, version=2)
        assert "SAFE V2" in text
        assert CONFIRMATION_MESSAGE in text

    def test_format_coupon_message_from_db(self, db_session, pub_settings):
        from app.models.football import Competition, Season, Team
        from app.models.market import Market
        from app.models.match import Match
        from app.models.prediction import AIModel
        from app.prediction.constants import MARKET_1X2, SELECTION_HOME

        comp = Competition(external_id=1, name="L1", country="FR")
        db_session.add(comp)
        db_session.flush()
        season = Season(competition_id=comp.id, external_id=2, name="2026", is_current=True)
        db_session.add(season)
        db_session.flush()
        home = Team(external_id=3, name="PSG")
        away = Team(external_id=4, name="OM")
        db_session.add_all([home, away])
        db_session.flush()
        match = Match(
            external_match_id=99,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc),
        )
        db_session.add(match)
        db_session.flush()
        market = Market(code=MARKET_1X2, name="1X2")
        model = AIModel(name="t", version="1", type="stat", active=True)
        db_session.add_all([market, model])
        db_session.flush()

        coupon = Coupon(type=CouponType.SAFE, status=CouponStatus.DRAFT, version=1)
        db_session.add(coupon)
        db_session.flush()
        pred = Prediction(
            match_id=match.id,
            market_id=market.id,
            model_id=model.id,
            model_version="1",
            selection=SELECTION_HOME,
            probability=Decimal("0.650000"),
            odds=Decimal("1.5000"),
            confidence=ConfidenceLevel.HIGH,
            risk_decision=RiskDecision.APPROVE.value,
        )
        db_session.add(pred)
        db_session.flush()
        db_session.add(CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=1))
        db_session.flush()

        text = format_coupon_message(coupon, pub_settings, detailed=True)
        assert "PSG vs OM" in text
        assert "COUPON SAFE" in text
