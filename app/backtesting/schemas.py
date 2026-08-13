"""Schémas backtesting, model registry et CLV."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.calibration.schemas import MarketMetrics


@dataclass
class BacktestConfig:
    """Configuration d'une variante de modèle à comparer."""

    label: str
    enable_dixon_coles: bool | None = None
    enable_ml: bool | None = None
    enable_calibration: bool | None = None

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "enable_dixon_coles": self.enable_dixon_coles,
            "enable_ml": self.enable_ml,
            "enable_calibration": self.enable_calibration,
        }


@dataclass
class BacktestReport:
    """Résultat d'un backtest walk-forward (sans data leakage)."""

    variant_label: str
    season_id: int
    matches_evaluated: int = 0
    matches_skipped: int = 0
    records_count: int = 0
    top1_accuracy: float = 0.0
    by_market: dict[str, MarketMetrics] = field(default_factory=dict)
    model_version: str = ""
    run_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "variant_label": self.variant_label,
            "season_id": self.season_id,
            "matches_evaluated": self.matches_evaluated,
            "matches_skipped": self.matches_skipped,
            "records_count": self.records_count,
            "top1_accuracy": round(self.top1_accuracy, 6),
            "by_market": {k: v.to_dict() for k, v in self.by_market.items()},
            "model_version": self.model_version,
            "run_at": self.run_at.isoformat() if self.run_at else None,
        }


@dataclass
class BacktestComparisonReport:
    """Comparaison de plusieurs variantes."""

    season_id: int
    variants: list[BacktestReport] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "season_id": self.season_id,
            "variants": [v.to_dict() for v in self.variants],
        }


@dataclass
class ModelVersionComparison:
    """Performance d'une version enregistrée."""

    model_id: int
    name: str
    version: str
    model_type: str
    active: bool
    metrics: dict
    trained_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "model_type": self.model_type,
            "active": self.active,
            "metrics": self.metrics,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
        }


@dataclass
class ClvAnalysisReport:
    """Analyse CLV sur prédictions publiées."""

    sample_size: int = 0
    avg_clv: float | None = None
    positive_clv_rate: float | None = None
    avg_opening_odds: float | None = None
    avg_closing_odds: float | None = None

    def to_dict(self) -> dict:
        return {
            "sample_size": self.sample_size,
            "avg_clv": round(self.avg_clv, 6) if self.avg_clv is not None else None,
            "positive_clv_rate": (
                round(self.positive_clv_rate, 6) if self.positive_clv_rate is not None else None
            ),
            "avg_opening_odds": (
                round(self.avg_opening_odds, 4) if self.avg_opening_odds is not None else None
            ),
            "avg_closing_odds": (
                round(self.avg_closing_odds, 4) if self.avg_closing_odds is not None else None
            ),
        }
