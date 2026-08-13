"""Tests unitaires — métriques calibration."""

import pytest

from app.calibration.metrics import (
    binary_brier,
    binary_log_loss,
    evaluate_market,
    multiclass_brier,
    multiclass_log_loss,
)
from app.calibration.schemas import MarketEvaluationRecord
from app.prediction.constants import MARKET_1X2, SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME


class TestCalibrationMetrics:
    def test_perfect_prediction_brier_zero(self):
        probs = {SELECTION_HOME: 1.0, SELECTION_DRAW: 0.0, SELECTION_AWAY: 0.0}
        assert multiclass_brier(probs, SELECTION_HOME) == 0.0

    def test_perfect_prediction_log_loss_zero(self):
        probs = {SELECTION_HOME: 1.0, SELECTION_DRAW: 0.0, SELECTION_AWAY: 0.0}
        assert multiclass_log_loss(probs, SELECTION_HOME) < 1e-10

    def test_binary_brier(self):
        assert binary_brier(0.8, True) == pytest.approx(0.04)
        assert binary_brier(0.8, False) == pytest.approx(0.64)

    def test_binary_log_loss(self):
        assert binary_log_loss(0.9, True) > 0
        assert binary_log_loss(0.9, False) > binary_log_loss(0.9, True)

    def test_evaluate_market(self):
        records = [
            MarketEvaluationRecord(
                match_id=1,
                market_code=MARKET_1X2,
                probabilities={SELECTION_HOME: 0.6, SELECTION_DRAW: 0.25, SELECTION_AWAY: 0.15},
                actual_selection=SELECTION_HOME,
            ),
            MarketEvaluationRecord(
                match_id=2,
                market_code=MARKET_1X2,
                probabilities={SELECTION_HOME: 0.4, SELECTION_DRAW: 0.3, SELECTION_AWAY: 0.3},
                actual_selection=SELECTION_AWAY,
            ),
        ]
        metrics = evaluate_market(records, MARKET_1X2, n_bins=5)
        assert metrics.sample_size == 2
        assert metrics.brier_score >= 0
        assert metrics.log_loss >= 0
        assert metrics.expected_calibration_error >= 0
