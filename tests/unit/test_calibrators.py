"""Tests unitaires — calibrateurs Platt / Isotonic."""

import numpy as np

from app.calibration.calibrators import BinaryCalibrator, MarketCalibrator
from app.calibration.constants import CALIBRATOR_ISOTONIC, CALIBRATOR_PLATT
from app.calibration.exceptions import CalibratorNotFittedError
from app.calibration.schemas import MarketEvaluationRecord
from app.prediction.constants import MARKET_1X2, SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME


def _synthetic_1x2_records(n: int = 40) -> list[MarketEvaluationRecord]:
    """Probabilités sur-confiantes pour tester la calibration."""
    rng = np.random.default_rng(42)
    records: list[MarketEvaluationRecord] = []
    for i in range(n):
        raw = rng.uniform(0.45, 0.85)
        actual = SELECTION_HOME if rng.random() < raw * 0.7 else SELECTION_AWAY
        if actual not in (SELECTION_HOME, SELECTION_AWAY):
            actual = SELECTION_DRAW
        remaining = 1.0 - raw
        records.append(
            MarketEvaluationRecord(
                match_id=i,
                market_code=MARKET_1X2,
                probabilities={
                    SELECTION_HOME: raw,
                    SELECTION_DRAW: remaining * 0.4,
                    SELECTION_AWAY: remaining * 0.6,
                },
                actual_selection=actual,
            )
        )
    return records


class TestBinaryCalibrator:
    def test_platt_fit_and_calibrate(self):
        probs = [0.9, 0.8, 0.7, 0.2, 0.3, 0.1, 0.85, 0.75, 0.15, 0.25]
        outcomes = [1, 1, 1, 0, 0, 0, 1, 1, 0, 0]
        cal = BinaryCalibrator(method=CALIBRATOR_PLATT)
        assert cal.fit(probs, outcomes) is True
        result = cal.calibrate(0.9)
        assert 0.0 < result < 1.0

    def test_isotonic_reduces_overconfidence(self):
        cal = BinaryCalibrator(method=CALIBRATOR_ISOTONIC)
        probs = [0.95] * 10 + [0.05] * 10
        outcomes = [1] * 5 + [0] * 5 + [0] * 5 + [1] * 5
        cal.fit(probs, outcomes)
        assert cal.calibrate(0.95) < 0.95

    def test_not_fitted_raises(self):
        cal = BinaryCalibrator(method=CALIBRATOR_PLATT)
        try:
            cal.calibrate(0.5)
            assert False, "Expected CalibratorNotFittedError"
        except CalibratorNotFittedError:
            pass


class TestMarketCalibrator:
    def test_calibrate_sums_to_one(self):
        records = _synthetic_1x2_records(50)
        calibrator = MarketCalibrator(market_code=MARKET_1X2, method=CALIBRATOR_ISOTONIC)
        selections = (SELECTION_HOME, SELECTION_DRAW, SELECTION_AWAY)
        assert calibrator.fit(records, selections) is True
        probs = {SELECTION_HOME: 0.7, SELECTION_DRAW: 0.2, SELECTION_AWAY: 0.1}
        calibrated = calibrator.calibrate(probs)
        assert abs(sum(calibrated.values()) - 1.0) < 1e-6
