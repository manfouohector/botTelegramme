"""Tests unitaires — PublicationService."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.config.settings import Settings
from app.coupons.schemas import CouponGenerationResult, GeneratedCoupon
from app.database.enums import CouponStatus, CouponType
from app.models.coupon import Coupon, CouponPrediction
from app.models.football import Competition, Season, Team
from app.models.market import Market
from app.models.match import Match
from app.models.prediction import AIModel, Prediction
from app.prediction.constants import MARKET_1X2, SELECTION_HOME
from app.repositories.coupon_repository import CouponRepository
from app.services.publication_service import PublicationService
from tests.fixtures.coupon_helpers import make_safe_pool


@pytest.fixture
def pub_settings():
    return Settings(
        _env_file=None,
        timezone="UTC",
        publication_enable=True,
        publication_confirm_if_unchanged=True,
        telegram_bot_token="123456:ABC",
        telegram_free_channel_id="@freechannel",
        telegram_premium_group_id="@premiumgroup",
    )


def _persist_free_coupon(db_session, *, external_suffix: int = 1) -> tuple[Coupon, Match]:
    comp = Competition(external_id=700 + external_suffix, name="L1", country="FR")
    db_session.add(comp)
    db_session.flush()
    season = Season(
        competition_id=comp.id,
        external_id=800 + external_suffix,
        name="2026",
        is_current=True,
    )
    db_session.add(season)
    db_session.flush()
    home = Team(external_id=900 + external_suffix, name="PSG")
    away = Team(external_id=910 + external_suffix, name="OM")
    db_session.add_all([home, away])
    db_session.flush()
    match = Match(
        external_match_id=1000 + external_suffix,
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

    coupon = Coupon(type=CouponType.FREE, status=CouponStatus.DRAFT, version=1)
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
    )
    db_session.add(pred)
    db_session.flush()
    db_session.add(CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=1))
    db_session.flush()
    return coupon, match


class TestPublicationService:
    async def test_skipped_when_disabled(self, db_session):
        settings = Settings(_env_file=None, publication_enable=False)
        bot = AsyncMock()
        result = await PublicationService(db_session, settings).publish_from_generation(
            bot,
            CouponGenerationResult(),
        )
        assert result.items == []
        bot.send_message.assert_not_awaited()

    async def test_publish_free_coupon(self, db_session, pub_settings):
        coupon, _match = _persist_free_coupon(db_session)
        generated = GeneratedCoupon(
            coupon_type=CouponType.FREE,
            candidates=make_safe_pool(1),
            total_odds=1.5,
            coupon_id=coupon.id,
        )
        gen_result = CouponGenerationResult(free=generated)

        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=42))

        batch = await PublicationService(db_session, pub_settings).publish_from_generation(
            bot,
            gen_result,
            phase="free",
            target_date=datetime(2026, 8, 20).date(),
        )

        assert batch.published_count == 1
        bot.send_message.assert_awaited_once()
        refreshed = db_session.get(Coupon, coupon.id)
        assert refreshed.status == CouponStatus.PUBLISHED

    async def test_confirm_if_unchanged(self, db_session, pub_settings):
        published, match = _persist_free_coupon(db_session, external_suffix=1)
        repo = CouponRepository(db_session)
        repo.publish_coupon(published.id)
        published.published_at = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
        db_session.flush()

        published_pred = published.predictions[0].prediction
        duplicate = Coupon(type=CouponType.FREE, status=CouponStatus.DRAFT, version=1)
        db_session.add(duplicate)
        db_session.flush()
        twin_pred = Prediction(
            match_id=match.id,
            market_id=published_pred.market_id,
            model_id=published_pred.model_id,
            model_version="1",
            selection=SELECTION_HOME,
            probability=Decimal("0.650000"),
            odds=Decimal("1.5000"),
        )
        db_session.add(twin_pred)
        db_session.flush()
        db_session.add(
            CouponPrediction(coupon_id=duplicate.id, prediction_id=twin_pred.id, position=1)
        )
        db_session.flush()

        generated = GeneratedCoupon(
            coupon_type=CouponType.FREE,
            candidates=make_safe_pool(1),
            total_odds=1.5,
            coupon_id=duplicate.id,
        )

        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=99))

        batch = await PublicationService(db_session, pub_settings).publish_from_generation(
            bot,
            CouponGenerationResult(free=generated),
            phase="free",
            target_date=datetime(2026, 8, 20).date(),
        )

        assert batch.any_confirmed
        assert db_session.get(Coupon, duplicate.id).status == CouponStatus.CANCELLED

    async def test_premium_phase_skips_free(self, db_session, pub_settings):
        coupon, _ = _persist_free_coupon(db_session)
        generated = GeneratedCoupon(
            coupon_type=CouponType.FREE,
            candidates=make_safe_pool(1),
            total_odds=1.5,
            coupon_id=coupon.id,
        )
        bot = AsyncMock()
        batch = await PublicationService(db_session, pub_settings).publish_from_generation(
            bot,
            CouponGenerationResult(free=generated),
            phase="premium",
        )
        assert batch.published_count == 0
        bot.send_message.assert_not_awaited()
