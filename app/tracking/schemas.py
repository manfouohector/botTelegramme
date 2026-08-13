"""Schémas Tracking Engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from app.database.enums import CouponType


@dataclass
class MetricRecord:
    """Enregistrement pour calcul de métriques."""

    is_correct: bool
    probability: float
    decimal_odds: float | None
    clv: float | None
    market_code: str
    coupon_type: str | None
    model_version: str


@dataclass
class SettlementResult:
    """Résultat du settlement d'une prédiction."""

    prediction_id: int
    match_id: int
    market_code: str
    selection: str
    actual_result: str
    is_correct: bool
    clv: float | None = None
    already_settled: bool = False

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "market_code": self.market_code,
            "selection": self.selection,
            "actual_result": self.actual_result,
            "is_correct": self.is_correct,
            "clv": round(self.clv, 6) if self.clv is not None else None,
            "already_settled": self.already_settled,
        }


@dataclass
class CouponSettlementResult:
    """Résultat du settlement d'un coupon."""

    coupon_id: int
    coupon_type: CouponType
    is_won: bool
    selections_total: int
    selections_correct: int
    combined_odds: float
    theoretical_profit: float
    already_settled: bool = False

    def to_dict(self) -> dict:
        return {
            "coupon_id": self.coupon_id,
            "coupon_type": self.coupon_type.value,
            "is_won": self.is_won,
            "selections_total": self.selections_total,
            "selections_correct": self.selections_correct,
            "combined_odds": round(self.combined_odds, 4),
            "theoretical_profit": round(self.theoretical_profit, 4),
            "already_settled": self.already_settled,
        }


@dataclass
class SettlementBatchResult:
    """Résultat d'un batch de settlement."""

    predictions_settled: int = 0
    predictions_skipped: int = 0
    coupons_settled: int = 0
    coupons_skipped: int = 0
    prediction_results: list[SettlementResult] = field(default_factory=list)
    coupon_results: list[CouponSettlementResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "predictions_settled": self.predictions_settled,
            "predictions_skipped": self.predictions_skipped,
            "coupons_settled": self.coupons_settled,
            "coupons_skipped": self.coupons_skipped,
            "prediction_results": [r.to_dict() for r in self.prediction_results],
            "coupon_results": [r.to_dict() for r in self.coupon_results],
        }


@dataclass
class PerformanceBreakdown:
    """Performance agrégée sur une dimension."""

    key: str
    sample_size: int
    accuracy: float
    roi: float
    avg_brier: float | None = None
    avg_log_loss: float | None = None
    avg_clv: float | None = None

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "sample_size": self.sample_size,
            "accuracy": round(self.accuracy, 6),
            "roi": round(self.roi, 6),
            "avg_brier": round(self.avg_brier, 6) if self.avg_brier is not None else None,
            "avg_log_loss": round(self.avg_log_loss, 6) if self.avg_log_loss is not None else None,
            "avg_clv": round(self.avg_clv, 6) if self.avg_clv is not None else None,
        }


@dataclass
class TrackingMetrics:
    """Métriques globales de performance."""

    sample_size: int
    accuracy: float
    roi: float
    avg_brier: float | None = None
    avg_log_loss: float | None = None
    avg_clv: float | None = None
    by_market: list[PerformanceBreakdown] = field(default_factory=list)
    by_coupon_type: list[PerformanceBreakdown] = field(default_factory=list)
    by_model_version: list[PerformanceBreakdown] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sample_size": self.sample_size,
            "accuracy": round(self.accuracy, 6),
            "roi": round(self.roi, 6),
            "avg_brier": round(self.avg_brier, 6) if self.avg_brier is not None else None,
            "avg_log_loss": round(self.avg_log_loss, 6) if self.avg_log_loss is not None else None,
            "avg_clv": round(self.avg_clv, 6) if self.avg_clv is not None else None,
            "by_market": [b.to_dict() for b in self.by_market],
            "by_coupon_type": [b.to_dict() for b in self.by_coupon_type],
            "by_model_version": [b.to_dict() for b in self.by_model_version],
        }


@dataclass
class HistoryEntry:
    """Entrée d'historique pour affichage / API."""

    prediction_id: int
    match_id: int
    market_code: str
    selection: str
    actual_result: str
    is_correct: bool
    probability: float
    decimal_odds: float | None
    clv: float | None
    model_version: str
    settled_at: datetime
    coupon_id: int | None = None
    coupon_type: CouponType | None = None
    home_team: str = ""
    away_team: str = ""

    def to_dict(self) -> dict:
        return {
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "market_code": self.market_code,
            "selection": self.selection,
            "actual_result": self.actual_result,
            "is_correct": self.is_correct,
            "probability": round(self.probability, 6),
            "decimal_odds": round(self.decimal_odds, 4) if self.decimal_odds is not None else None,
            "clv": round(self.clv, 6) if self.clv is not None else None,
            "model_version": self.model_version,
            "settled_at": self.settled_at.isoformat(),
            "coupon_id": self.coupon_id,
            "coupon_type": self.coupon_type.value if self.coupon_type else None,
            "home_team": self.home_team,
            "away_team": self.away_team,
        }
