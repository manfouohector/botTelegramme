"""Tests unitaires — ClvService."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.backtesting.clv_service import ClvService
from app.config.settings import Settings
from app.database.enums import CouponStatus, CouponType, MatchStatus
from app.models.coupon import Coupon, CouponPrediction
from app.models.market import Market, Odd
from app.models.prediction import AIModel, Prediction, PredictionResult
from app.prediction.constants import MARKET_1X2, SELECTION_HOME
from app.tracking.tracking_engine import TrackingEngine
from tests.fixtures.feature_helpers import seed_feature_test_data


@pytest.fixture
def clv_settings():
    return Settings(
        _env_file=None,
        clv_update_hours_before_kickoff=2,
        tracking_settle_days_back=30,
    )


class TestClvService:
    def _setup_published_coupon(self, db_session, *, with_odds: bool = True):
        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        market = db_session.scalar(select(Market).where(Market.code == MARKET_1X2))
        if market is None:
            market = Market(code=MARKET_1X2, name="1X2", active=True)
            db_session.add(market)
            db_session.flush()

        model = AIModel(name="test", version="1.0", type="statistical", active=True)
        db_session.add(model)
        db_session.flush()

        pred = Prediction(
            match_id=match.id,
            market_id=market.id,
            model_id=model.id,
            model_version="1.0.0",
            selection=SELECTION_HOME,
            probability=Decimal("0.650000"),
            odds=None,
        )
        db_session.add(pred)
        db_session.flush()

        if with_odds:
            db_session.add(
                Odd(
                    match_id=match.id,
                    market_id=market.id,
                    bookmaker="pinnacle",
                    selection=SELECTION_HOME,
                    odds=Decimal("1.9000"),
                    fetched_at=datetime.now(timezone.utc),
                )
            )
            db_session.flush()

        coupon = Coupon(type=CouponType.FREE, status=CouponStatus.PUBLISHED, version=1)
        db_session.add(coupon)
        db_session.flush()
        db_session.add(CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=1))
        db_session.flush()
        return coupon, pred, match

    def test_record_publication_odds(self, db_session, clv_settings):
        coupon, pred, _match = self._setup_published_coupon(db_session)
        updated = ClvService(db_session, clv_settings).record_publication_odds(coupon.id)

        assert updated == 1
        db_session.refresh(pred)
        assert pred.odds is not None
        assert float(pred.odds) == pytest.approx(1.9)

    def test_refresh_closing_odds(self, db_session, clv_settings):
        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        match.scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        match.status = MatchStatus.SCHEDULED
        db_session.flush()

        market = Market(code=MARKET_1X2, name="1X2", active=True)
        db_session.add(market)
        db_session.flush()
        db_session.add(
            Odd(
                match_id=match.id,
                market_id=market.id,
                bookmaker="pinnacle",
                selection=SELECTION_HOME,
                odds=Decimal("1.7500"),
                fetched_at=datetime.now(timezone.utc),
            )
        )
        db_session.flush()

        count = ClvService(db_session, clv_settings).refresh_closing_odds()
        assert count >= 1

        row = db_session.scalar(
            select(Odd).where(Odd.match_id == match.id, Odd.selection == SELECTION_HOME)
        )
        assert row.closing_odds is not None

    def test_compute_clv_for_prediction(self, db_session, clv_settings):
        coupon, pred, match = self._setup_published_coupon(db_session)
        ClvService(db_session, clv_settings).record_publication_odds(coupon.id)

        row = db_session.scalar(
            select(Odd).where(Odd.match_id == match.id, Odd.selection == SELECTION_HOME)
        )
        row.closing_odds = Decimal("1.7000")
        db_session.flush()

        clv = ClvService(db_session, clv_settings).compute_clv_for_prediction(pred.id)
        assert clv == pytest.approx(1.9 / 1.7 - 1, rel=1e-4)

    def test_analyze_published_clv(self, db_session, clv_settings):
        coupon, pred, match = self._setup_published_coupon(db_session)
        service = ClvService(db_session, clv_settings)
        service.record_publication_odds(coupon.id)

        db_session.add(
            Odd(
                match_id=match.id,
                market_id=pred.market_id,
                bookmaker="pinnacle",
                selection=SELECTION_HOME,
                odds=Decimal("1.7000"),
                closing_odds=Decimal("1.7000"),
                fetched_at=datetime.now(timezone.utc),
            )
        )
        db_session.flush()

        match.status = MatchStatus.FINISHED
        match.home_score = 2
        match.away_score = 1
        db_session.flush()

        TrackingEngine(db_session, clv_settings).settle_prediction(pred)

        report = service.analyze_published_clv()
        assert report.sample_size >= 1
        assert report.avg_clv is not None

    def test_lazy_import(self):
        from app.backtesting import BacktestEngine, ClvService, ModelRegistry

        assert BacktestEngine is not None
        assert ClvService is not None
        assert ModelRegistry is not None
