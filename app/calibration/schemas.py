"""Schémas calibration et évaluation."""

from dataclasses import dataclass, field

from app.prediction.schemas import MarketProbabilities, MatchPrediction


@dataclass
class MarketEvaluationRecord:
    """Prédiction vs résultat réel pour un marché."""

    match_id: int
    market_code: str
    probabilities: dict[str, float]
    actual_selection: str


@dataclass
class CalibrationBin:
    """Bin pour courbe de calibration."""

    bin_lower: float
    bin_upper: float
    avg_predicted: float
    avg_actual: float
    count: int

    def to_dict(self) -> dict:
        return {
            "bin_lower": round(self.bin_lower, 4),
            "bin_upper": round(self.bin_upper, 4),
            "avg_predicted": round(self.avg_predicted, 4),
            "avg_actual": round(self.avg_actual, 4),
            "count": self.count,
        }


@dataclass
class MarketMetrics:
    """Métriques d'évaluation par marché."""

    market_code: str
    sample_size: int
    brier_score: float
    log_loss: float
    expected_calibration_error: float
    calibration_bins: list[CalibrationBin] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "market_code": self.market_code,
            "sample_size": self.sample_size,
            "brier_score": round(self.brier_score, 6),
            "log_loss": round(self.log_loss, 6),
            "expected_calibration_error": round(self.expected_calibration_error, 6),
            "calibration_bins": [b.to_dict() for b in self.calibration_bins],
        }


@dataclass
class EvaluationReport:
    """Rapport d'évaluation avant/après calibration."""

    sample_size: int
    method: str
    raw_metrics: dict[str, MarketMetrics]
    calibrated_metrics: dict[str, MarketMetrics] | None = None

    def to_dict(self) -> dict:
        result = {
            "sample_size": self.sample_size,
            "method": self.method,
            "raw_metrics": {k: v.to_dict() for k, v in self.raw_metrics.items()},
        }
        if self.calibrated_metrics:
            result["calibrated_metrics"] = {
                k: v.to_dict() for k, v in self.calibrated_metrics.items()
            }
        return result


@dataclass
class CalibratedMatchPrediction:
    """Prédiction avec probabilités calibrées."""

    raw: MatchPrediction
    markets: list[MarketProbabilities]
    calibration_method: str
    calibration_version: str
    metadata: dict = field(default_factory=dict)

    @property
    def match_id(self) -> int:
        return self.raw.match_id

    @property
    def confidence(self):
        return self.raw.confidence

    def get_probability(self, market_code: str, selection: str) -> float | None:
        for market in self.markets:
            if market.market_code == market_code:
                return market.probabilities.get(selection)
        return None

    def to_dict(self) -> dict:
        return {
            "match_id": self.raw.match_id,
            "calibration_method": self.calibration_method,
            "calibration_version": self.calibration_version,
            "raw": self.raw.to_dict(),
            "calibrated_markets": [m.to_dict() for m in self.markets],
            "metadata": self.metadata,
        }
