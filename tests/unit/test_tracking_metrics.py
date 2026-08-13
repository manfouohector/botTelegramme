"""Tests unitaires — métriques tracking."""

import pytest

from app.tracking.metrics import aggregate_metrics, calculate_clv, unit_stake_profit
from app.tracking.schemas import MetricRecord


class TestTrackingMetrics:
    def test_calculate_clv(self):
        assert calculate_clv(2.0, 1.8) == pytest.approx(0.111111, rel=1e-4)

    def test_unit_stake_profit_win(self):
        assert unit_stake_profit(is_correct=True, decimal_odds=2.5) == pytest.approx(1.5)

    def test_unit_stake_profit_loss(self):
        assert unit_stake_profit(is_correct=False, decimal_odds=2.5) == -1.0

    def test_aggregate_metrics_empty(self):
        metrics = aggregate_metrics([])
        assert metrics.sample_size == 0
        assert metrics.accuracy == 0.0

    def test_aggregate_metrics_accuracy_and_roi(self):
        records = [
            MetricRecord(True, 0.7, 2.0, 0.05, "1X2", "SAFE", "1.0.0"),
            MetricRecord(False, 0.6, 1.8, None, "BTTS", "VALUE", "1.0.0"),
            MetricRecord(True, 0.55, 1.5, 0.02, "OU25", "FREE", "1.0.0"),
        ]
        metrics = aggregate_metrics(records)
        assert metrics.sample_size == 3
        assert metrics.accuracy == pytest.approx(2 / 3)
        assert metrics.roi == pytest.approx((1.0 + (-1.0) + 0.5) / 3)
        assert metrics.avg_brier is not None
        assert metrics.avg_log_loss is not None
        assert len(metrics.by_market) == 3
        assert len(metrics.by_coupon_type) == 3
