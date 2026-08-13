"""Tests unitaires/intégration — TrackingEngine."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.config.settings import Settings
from app.database.enums import CouponStatus, CouponType, MatchStatus
from app.models.coupon import Coupon
from app.models.market import Market, Odd
from app.models.prediction import AIModel, Prediction, PredictionResult
from app.prediction.constants import MARKET_1X2, SELECTION_HOME
from app.tracking.exceptions import MatchNotSettleableError
from app.tracking.tracking_engine import TrackingEngine
from tests.fixtures.feature_helpers import seed_feature_test_data


class TestTrackingEngine:
    @pytest.fixture
    def settings(self):
        return Settings(_env_file=None, tracking_settle_days_back=30)

    @pytest.fixture
    def finished_match_setup(self, db_session):
        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        match.status = MatchStatus.FINISHED
        match.home_score = 2
        match.away_score = 1
        db_session.flush()
        return match

    def _add_prediction(self, db_session, match, *, selection=SELECTION_HOME, odds=2.0):
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
            selection=selection,
            probability=Decimal("0.680000"),
            odds=Decimal(str(odds)),
        )
        db_session.add(pred)
        db_session.flush()
        return pred

    def test_settle_prediction_correct(self, db_session, settings, finished_match_setup):
        pred = self._add_prediction(db_session, finished_match_setup)
        result = TrackingEngine(db_session, settings).settle_prediction(pred)
        assert result is not None
        assert result.is_correct is True
        assert result.actual_result == SELECTION_HOME
        assert result.already_settled is False

        saved = db_session.scalar(
            select(PredictionResult).where(PredictionResult.prediction_id == pred.id)
        )
        assert saved is not None
        assert saved.is_correct is True

    def test_settle_prediction_incorrect(self, db_session, settings, finished_match_setup):
        from app.prediction.constants import SELECTION_AWAY

        pred = self._add_prediction(db_session, finished_match_setup, selection=SELECTION_AWAY)
        result = TrackingEngine(db_session, settings).settle_prediction(pred)
        assert result is not None
        assert result.is_correct is False

    def test_settle_prediction_idempotent(self, db_session, settings, finished_match_setup):
        pred = self._add_prediction(db_session, finished_match_setup)
        engine = TrackingEngine(db_session, settings)
        first = engine.settle_prediction(pred)
        second = engine.settle_prediction(
            engine.repo.get_prediction_with_relations(pred.id)
        )
        assert first is not None
        assert second is not None
        assert second.already_settled is True
        count = db_session.scalar(
            select(PredictionResult).where(PredictionResult.prediction_id == pred.id)
        )
        assert count is not None

    def test_settle_match_batch(self, db_session, settings, finished_match_setup):
        self._add_prediction(db_session, finished_match_setup)
        results = TrackingEngine(db_session, settings).settle_match(finished_match_setup.id)
        assert len(results) == 1

    def test_settle_match_not_finished_raises(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        with pytest.raises(MatchNotSettleableError):
            TrackingEngine(db_session, settings).settle_match(match.id)

    def test_settle_coupon_won(self, db_session, settings, finished_match_setup):
        preds = [
            self._add_prediction(db_session, finished_match_setup, odds=1.8),
        ]
        coupon = Coupon(type=CouponType.FREE, status=CouponStatus.PUBLISHED, version=1)
        db_session.add(coupon)
        db_session.flush()
        from app.models.coupon import CouponPrediction

        for i, pred in enumerate(preds, start=1):
            db_session.add(
                CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=i)
            )
        db_session.flush()

        for pred in preds:
            TrackingEngine(db_session, settings).settle_prediction(pred)

        result = TrackingEngine(db_session, settings).settle_coupon(coupon)
        assert result.is_won is True
        assert coupon.status == CouponStatus.SETTLED

    def test_settle_coupon_lost(self, db_session, settings, finished_match_setup):
        from app.prediction.constants import SELECTION_AWAY

        pred = self._add_prediction(
            db_session, finished_match_setup, selection=SELECTION_AWAY, odds=2.5
        )
        coupon = Coupon(type=CouponType.SAFE, status=CouponStatus.PUBLISHED, version=1)
        db_session.add(coupon)
        db_session.flush()
        from app.models.coupon import CouponPrediction

        db_session.add(CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=1))
        db_session.flush()

        TrackingEngine(db_session, settings).settle_prediction(pred)
        result = TrackingEngine(db_session, settings).settle_coupon(coupon)
        assert result.is_won is False
        assert result.theoretical_profit == -1.0

    def test_settle_pending_batch(self, db_session, settings, finished_match_setup):
        self._add_prediction(db_session, finished_match_setup)
        batch = TrackingEngine(db_session, settings).settle_pending()
        assert batch.predictions_settled >= 1

    def test_clv_with_closing_odds(self, db_session, settings, finished_match_setup):
        pred = self._add_prediction(db_session, finished_match_setup, odds=2.0)
        db_session.add(
            Odd(
                match_id=finished_match_setup.id,
                market_id=pred.market_id,
                bookmaker="test",
                selection=SELECTION_HOME,
                odds=Decimal("1.8000"),
                closing_odds=Decimal("1.8000"),
                fetched_at=datetime.now(timezone.utc),
            )
        )
        db_session.flush()
        result = TrackingEngine(db_session, settings).settle_prediction(pred)
        assert result is not None
        assert result.clv == pytest.approx(0.111111, rel=1e-4)

    def test_get_metrics_and_history(self, db_session, settings, finished_match_setup):
        pred = self._add_prediction(db_session, finished_match_setup)
        engine = TrackingEngine(db_session, settings)
        engine.settle_prediction(pred)

        metrics = engine.get_metrics()
        assert metrics.sample_size >= 1
        assert metrics.accuracy >= 0.0

        history = engine.get_history(limit=10)
        assert len(history) >= 1
        assert history[0].is_correct is True

    def test_settle_via_coupon_generator_flow(self, db_session, settings, finished_match_setup):
        """Intégration : prédiction persistée puis settlement batch."""
        pred = self._add_prediction(db_session, finished_match_setup)
        batch = TrackingEngine(db_session, settings).settle_pending()
        assert batch.predictions_settled >= 1
        assert pred.id in {r.prediction_id for r in batch.prediction_results}

    def test_lazy_import(self):
        from app.tracking import TrackingEngine, SettlementResult

        assert TrackingEngine is not None
        assert SettlementResult is not None
