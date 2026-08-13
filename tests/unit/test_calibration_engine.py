"""Tests unitaires/intégration — CalibrationEngine."""

import tempfile
from pathlib import Path

import pytest

from app.calibration.calibration_engine import CalibrationEngine
from app.calibration.constants import CALIBRATOR_ISOTONIC, CALIBRATOR_NONE
from app.calibration.exceptions import InsufficientCalibrationDataError
from app.calibration.schemas import MarketEvaluationRecord
from app.config.settings import Settings
from app.prediction.constants import MARKET_1X2, MARKET_BTTS, MARKET_OU25
from tests.fixtures.feature_helpers import seed_feature_test_data
from tests.unit.test_calibrators import _synthetic_1x2_records


def _full_synthetic_records(n: int = 40) -> list[MarketEvaluationRecord]:
    base = _synthetic_1x2_records(n)
    extra: list[MarketEvaluationRecord] = []
    for i, rec in enumerate(base):
        extra.append(
            MarketEvaluationRecord(
                match_id=rec.match_id + 1000,
                market_code=MARKET_BTTS,
                probabilities={"YES": 0.55, "NO": 0.45},
                actual_selection="YES" if i % 2 == 0 else "NO",
            )
        )
        extra.append(
            MarketEvaluationRecord(
                match_id=rec.match_id + 2000,
                market_code=MARKET_OU25,
                probabilities={"OVER": 0.52, "UNDER": 0.48},
                actual_selection="OVER" if i % 3 == 0 else "UNDER",
            )
        )
    return base + extra


def _sample_match_prediction():
    """Prédiction synthétique — évite le pipeline complet dans les tests unitaires."""
    from app.database.enums import ConfidenceLevel
    from app.prediction.constants import SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME
    from app.prediction.schemas import MarketProbabilities, MatchPrediction

    return MatchPrediction(
        match_id=1,
        external_match_id=99999,
        home_lambda=1.6,
        away_lambda=1.0,
        markets=[
            MarketProbabilities(
                MARKET_1X2,
                {SELECTION_HOME: 0.62, SELECTION_DRAW: 0.22, SELECTION_AWAY: 0.16},
                "POISSON",
            ),
            MarketProbabilities(MARKET_BTTS, {"YES": 0.58, "NO": 0.42}, "POISSON"),
            MarketProbabilities(MARKET_OU25, {"OVER": 0.54, "UNDER": 0.46}, "POISSON"),
        ],
        model_type="POISSON",
        model_version="1.0.0",
        confidence=ConfidenceLevel.MEDIUM,
    )


class TestCalibrationEngine:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            calibration_enable=True,
            calibration_method="isotonic",
            calibration_min_samples=30,
            calibration_bins=5,
            prediction_enable_ml=False,
            feature_min_matches=3,
            prediction_min_matches=3,
        )

    def test_fit_and_calibrate(self, db_session, settings):
        engine = CalibrationEngine(db_session, settings)
        records = _full_synthetic_records(40)
        assert engine.fit(records) is True

        raw = _sample_match_prediction()
        calibrated = engine.calibrate(raw)

        assert calibrated.calibration_method == CALIBRATOR_ISOTONIC
        assert calibrated.get_probability(MARKET_1X2, "HOME") is not None
        m1x2 = next(m for m in calibrated.markets if m.market_code == MARKET_1X2)
        assert abs(sum(m1x2.probabilities.values()) - 1.0) < 1e-6

    def test_evaluate_improves_or_maintains(self, db_session, settings):
        engine = CalibrationEngine(db_session, settings)
        records = _full_synthetic_records(50)
        engine.fit(records)
        report = engine.evaluate(records)

        assert report.sample_size > 0
        assert MARKET_1X2 in report.raw_metrics
        assert report.calibrated_metrics is not None
        raw_brier = report.raw_metrics[MARKET_1X2].brier_score
        cal_brier = report.calibrated_metrics[MARKET_1X2].brier_score
        assert cal_brier <= raw_brier + 0.05

    def test_insufficient_samples_raises(self, db_session, settings):
        engine = CalibrationEngine(db_session, settings)
        with pytest.raises(InsufficientCalibrationDataError):
            engine.fit(_synthetic_1x2_records(5))

    def test_save_and_load(self, db_session, settings):
        engine = CalibrationEngine(db_session, settings)
        engine.fit(_full_synthetic_records(40))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cal.pkl"
            engine.save(path)

            engine2 = CalibrationEngine(db_session, settings)
            assert engine2.load(path) is True
            assert engine2.fitted is True

    def test_disabled_calibration(self, db_session, settings):
        settings.calibration_enable = False
        settings.calibration_method = "none"
        engine = CalibrationEngine(db_session, settings)
        assert engine.fit(_full_synthetic_records(40)) is False

        raw = _sample_match_prediction()
        calibrated = engine.calibrate(raw)
        assert calibrated.calibration_method == CALIBRATOR_NONE

    def test_evaluate_season(self, db_session, settings):
        settings.calibration_min_samples = 10
        settings.prediction_ml_min_samples = 100
        data = seed_feature_test_data(db_session)
        engine = CalibrationEngine(db_session, settings)
        report = engine.evaluate_season(
            data["season"].id,
            data["target_match"].scheduled_at,
            limit=5,
        )
        assert report.sample_size > 0
