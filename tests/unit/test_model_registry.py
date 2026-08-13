"""Tests unitaires — ModelRegistry."""

from datetime import datetime, timezone

import pytest

from app.backtesting.exceptions import ModelRegistryError
from app.backtesting.model_registry import ModelRegistry
from app.backtesting.schemas import BacktestReport
from app.config.settings import Settings


@pytest.fixture
def registry_settings():
    return Settings(_env_file=None)


def _sample_report(*, label: str = "poisson", version: str = "1.0.0") -> BacktestReport:
    return BacktestReport(
        variant_label=label,
        season_id=1,
        matches_evaluated=10,
        records_count=30,
        top1_accuracy=0.55,
        model_version=version,
        run_at=datetime.now(timezone.utc),
    )


class TestModelRegistry:
    def test_register_and_list_versions(self, db_session, registry_settings):
        registry = ModelRegistry(db_session, registry_settings)
        first = registry.register_backtest(_sample_report(label="poisson", version="1.0.0"))
        second = registry.register_backtest(_sample_report(label="dixon_coles", version="1.0.1"))

        poisson_versions = registry.list_versions("backtest_poisson")
        assert len(poisson_versions) == 1
        assert first.id == poisson_versions[0].id
        assert second.name == "backtest_dixon_coles"

    def test_upsert_updates_metrics_without_deleting_other_versions(self, db_session, registry_settings):
        registry = ModelRegistry(db_session, registry_settings)
        v1 = registry.register_backtest(_sample_report(label="ensemble", version="1.0.0"))
        v2 = registry.register_model(
            "backtest_ensemble",
            "2.0.0",
            "backtest",
            metrics={"top1_accuracy": 0.60},
        )

        updated = registry.register_backtest(
            BacktestReport(
                variant_label="ensemble",
                season_id=1,
                matches_evaluated=12,
                records_count=36,
                top1_accuracy=0.58,
                model_version="1.0.0",
                run_at=datetime.now(timezone.utc),
            )
        )

        assert updated.id == v1.id
        assert updated.metrics["top1_accuracy"] == 0.58
        versions = registry.list_versions("backtest_ensemble")
        assert len(versions) == 2
        assert {m.version for m in versions} == {"1.0.0", "2.0.0"}
        assert v2.id in {m.id for m in versions}

    def test_compare_versions_and_activate(self, db_session, registry_settings):
        registry = ModelRegistry(db_session, registry_settings)
        a = registry.register_model("xgb", "1.0.0", "ml", metrics={"accuracy": 0.52})
        b = registry.register_model("xgb", "1.1.0", "ml", metrics={"accuracy": 0.54}, activate=True)

        comparisons = registry.compare_versions("xgb")
        assert len(comparisons) == 2
        active = registry.get_active("xgb")
        assert active is not None
        assert active.id == b.id

        registry.set_active(a.id)
        assert registry.get_active("xgb").id == a.id

    def test_set_active_missing_raises(self, db_session, registry_settings):
        with pytest.raises(ModelRegistryError):
            ModelRegistry(db_session, registry_settings).set_active(99999)
