"""Model Registry — versions et comparaison de performances."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.backtesting.exceptions import ModelRegistryError
from app.backtesting.schemas import BacktestReport, ModelVersionComparison
from app.config.settings import Settings, get_settings
from app.models.prediction import AIModel
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class ModelRegistry:
    """
    Enregistre et compare les versions de modèles.

    Ne remplace jamais l'historique — chaque version est persistée séparément.
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.repo = ModelRegistryRepository(session)

    def register_backtest(
        self,
        report: BacktestReport,
        *,
        model_type: str = "backtest",
        activate: bool = False,
    ) -> AIModel:
        """Enregistre les métriques d'un backtest comme version de modèle."""
        if not report.variant_label:
            raise ModelRegistryError("variant_label requis")

        version = report.model_version or report.variant_label
        name = f"backtest_{report.variant_label}"
        metrics = report.to_dict()

        model = self.repo.upsert_model(
            name=name,
            version=version,
            model_type=model_type,
            metrics=metrics,
            trained_at=report.run_at or datetime.now(timezone.utc),
            activate=activate,
        )
        log_event(
            logger,
            "MODEL_REGISTERED",
            name=name,
            version=version,
            accuracy=round(report.top1_accuracy, 4),
        )
        return model

    def register_model(
        self,
        name: str,
        version: str,
        model_type: str,
        *,
        metrics: dict | None = None,
        activate: bool = False,
    ) -> AIModel:
        """Enregistrement manuel d'un modèle."""
        return self.repo.upsert_model(
            name=name,
            version=version,
            model_type=model_type,
            metrics=metrics or {},
            trained_at=datetime.now(timezone.utc),
            activate=activate,
        )

    def list_versions(self, name: str) -> list[AIModel]:
        return self.repo.list_by_name(name)

    def compare_versions(self, name: str) -> list[ModelVersionComparison]:
        """Compare les performances de toutes les versions d'un modèle."""
        models = self.repo.list_by_name(name)
        comparisons: list[ModelVersionComparison] = []
        for model in models:
            comparisons.append(
                ModelVersionComparison(
                    model_id=model.id,
                    name=model.name,
                    version=model.version,
                    model_type=model.type,
                    active=model.active,
                    metrics=model.metrics or {},
                    trained_at=model.trained_at,
                )
            )
        return comparisons

    def get_active(self, name: str) -> AIModel | None:
        return self.repo.get_active(name)

    def set_active(self, model_id: int) -> AIModel | None:
        model = self.repo.get_by_id(model_id)
        if model is None:
            raise ModelRegistryError(f"Modèle {model_id} introuvable")
        return self.repo.activate(model_id)
