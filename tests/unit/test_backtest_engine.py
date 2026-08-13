"""Tests unitaires — BacktestEngine."""

from datetime import datetime, timezone

import pytest

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.exceptions import InsufficientBacktestDataError
from app.backtesting.schemas import BacktestConfig
from app.config.settings import Settings
from tests.fixtures.feature_helpers import seed_feature_test_data


@pytest.fixture
def backtest_settings():
    return Settings(
        _env_file=None,
        backtest_min_matches=3,
        backtest_default_limit=20,
        prediction_enable_ml=False,
        prediction_enable_dixon_coles=True,
        prediction_min_matches=3,
        feature_min_matches=3,
        feature_form_window=5,
        calibration_bins=5,
    )


class TestBacktestEngine:
    def test_run_walk_forward(self, db_session, backtest_settings):
        data = seed_feature_test_data(db_session)
        before = datetime(2026, 8, 22, tzinfo=timezone.utc)
        report = BacktestEngine(db_session, backtest_settings).run(
            data["season"].id,
            before,
            limit=5,
        )

        assert report.matches_evaluated > 0
        assert report.records_count > 0
        assert 0.0 <= report.top1_accuracy <= 1.0
        assert report.variant_label == "default"
        assert report.model_version

    def test_compare_variants(self, db_session, backtest_settings):
        data = seed_feature_test_data(db_session)
        before = datetime(2026, 8, 22, tzinfo=timezone.utc)
        comparison = BacktestEngine(db_session, backtest_settings).compare_variants(
            data["season"].id,
            before,
            limit=4,
        )

        assert comparison.season_id == data["season"].id
        assert len(comparison.variants) == 3
        labels = {v.variant_label for v in comparison.variants}
        assert labels == {"poisson", "dixon_coles", "ensemble"}

    def test_insufficient_data_raises(self, db_session, backtest_settings):
        data = seed_feature_test_data(db_session)
        before = datetime(2026, 8, 1, tzinfo=timezone.utc)
        with pytest.raises(InsufficientBacktestDataError):
            BacktestEngine(db_session, backtest_settings).run(
                data["season"].id,
                before,
                limit=2,
            )

    def test_custom_variant_config(self, db_session, backtest_settings):
        data = seed_feature_test_data(db_session)
        before = datetime(2026, 8, 22, tzinfo=timezone.utc)
        cfg = BacktestConfig(label="poisson_only", enable_dixon_coles=False, enable_ml=False)
        report = BacktestEngine(db_session, backtest_settings).run(
            data["season"].id,
            before,
            config=cfg,
            limit=4,
            record_run=False,
        )
        assert report.variant_label == "poisson_only"
