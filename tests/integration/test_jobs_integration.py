"""Tests d'intégration — jobs planifiés avec session réelle."""

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy import select

from app.database.enums import CouponStatus, CouponType, MatchStatus
from app.jobs.constants import JOB_SETTLEMENT
from app.jobs.tasks import run_job_sync, run_settlement
from app.models.coupon import Coupon, CouponPrediction
from app.models.market import Market
from app.models.prediction import AIModel, Prediction
from app.prediction.constants import MARKET_1X2, SELECTION_HOME
from tests.fixtures.feature_helpers import seed_feature_test_data


def _session_scope_factory(session):
    @contextmanager
    def _scope(_settings):
        yield session

    return _scope


class TestJobsIntegration:
    def test_settlement_job_processes_pending(self, db_session, integration_settings):
        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        match.status = MatchStatus.FINISHED
        match.home_score = 2
        match.away_score = 1
        db_session.flush()

        market = db_session.scalar(select(Market).where(Market.code == MARKET_1X2))
        if market is None:
            market = Market(code=MARKET_1X2, name="1X2", active=True)
            db_session.add(market)
            db_session.flush()

        model = AIModel(name="job_test", version="1.0", type="statistical", active=True)
        db_session.add(model)
        db_session.flush()

        pred = Prediction(
            match_id=match.id,
            market_id=market.id,
            model_id=model.id,
            model_version="1.0.0",
            selection=SELECTION_HOME,
            probability=Decimal("0.650000"),
            odds=Decimal("1.8000"),
        )
        db_session.add(pred)
        db_session.flush()

        coupon = Coupon(type=CouponType.FREE, status=CouponStatus.PUBLISHED, version=1)
        db_session.add(coupon)
        db_session.flush()
        db_session.add(CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=1))
        db_session.flush()

        settings = integration_settings.model_copy(
            update={"database_url": "postgresql://test:test@localhost/test"}
        )

        with patch("app.jobs.tasks.session_scope", _session_scope_factory(db_session)):
            with patch("app.database.session.check_database_connection", return_value=True):
                result = run_settlement(settings)

        assert result.success is True
        assert result.details["predictions_settled"] >= 1
        assert result.details["coupons_settled"] >= 1

    def test_run_job_sync_settlement(self, db_session, integration_settings):
        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        match.status = MatchStatus.FINISHED
        match.home_score = 1
        match.away_score = 0
        db_session.flush()

        market = Market(code=MARKET_1X2, name="1X2", active=True)
        db_session.add(market)
        db_session.flush()
        model = AIModel(name="sync_test", version="1.0", type="statistical", active=True)
        db_session.add(model)
        db_session.flush()
        pred = Prediction(
            match_id=match.id,
            market_id=market.id,
            model_id=model.id,
            model_version="1.0.0",
            selection=SELECTION_HOME,
            probability=Decimal("0.600000"),
            odds=Decimal("1.5000"),
        )
        db_session.add(pred)
        db_session.flush()

        settings = integration_settings.model_copy(
            update={"database_url": "postgresql://test:test@localhost/test"}
        )

        with patch("app.jobs.tasks.session_scope", _session_scope_factory(db_session)):
            with patch("app.database.session.check_database_connection", return_value=True):
                result = run_job_sync(JOB_SETTLEMENT, settings)

        assert result.job_name == JOB_SETTLEMENT
        assert result.success is True

    def test_clv_refresh_job_window(self, db_session, integration_settings):
        from app.backtesting.clv_service import ClvService

        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        match.scheduled_at = datetime.now(timezone.utc) + timedelta(minutes=20)
        match.status = MatchStatus.SCHEDULED
        db_session.flush()

        market = Market(code=MARKET_1X2, name="1X2", active=True)
        db_session.add(market)
        db_session.flush()
        from app.models.market import Odd

        db_session.add(
            Odd(
                match_id=match.id,
                market_id=market.id,
                bookmaker="pinnacle",
                selection=SELECTION_HOME,
                odds=Decimal("1.8500"),
                fetched_at=datetime.now(timezone.utc),
            )
        )
        db_session.flush()

        updated = ClvService(db_session, integration_settings).refresh_closing_odds()
        assert updated >= 1
