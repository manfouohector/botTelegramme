"""Tests d'intégration — backtesting et model registry."""

from datetime import datetime, timezone

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.model_registry import ModelRegistry


class TestBacktestIntegration:
    def test_backtest_register_and_compare(self, db_session, integration_settings, seeded_match_day):
        before = datetime(2026, 8, 22, tzinfo=timezone.utc)
        engine = BacktestEngine(db_session, integration_settings)
        report = engine.run(
            seeded_match_day["season"].id,
            before,
            limit=5,
            record_run=False,
        )

        registry = ModelRegistry(db_session, integration_settings)
        model = registry.register_backtest(report, activate=True)
        assert model.active is True
        assert model.metrics["top1_accuracy"] == report.top1_accuracy

        comparisons = registry.compare_versions(model.name)
        assert len(comparisons) == 1
        assert comparisons[0].model_id == model.id

        second = engine.run(
            seeded_match_day["season"].id,
            before,
            limit=5,
            record_run=False,
        )
        registry.register_model(
            model.name,
            "alt_run",
            "backtest",
            metrics=second.to_dict(),
        )
        assert len(registry.list_versions(model.name)) == 2
