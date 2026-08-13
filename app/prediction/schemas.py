"""Schémas Prediction Engine."""

from dataclasses import dataclass, field

from app.database.enums import ConfidenceLevel


@dataclass
class MarketProbabilities:
    """Probabilités pour un marché."""

    market_code: str
    probabilities: dict[str, float]
    model_type: str

    def to_dict(self) -> dict:
        return {
            "market_code": self.market_code,
            "probabilities": {k: round(v, 6) for k, v in self.probabilities.items()},
            "model_type": self.model_type,
        }


@dataclass
class MatchPrediction:
    """Prédiction complète pour un match."""

    match_id: int
    external_match_id: int
    home_lambda: float
    away_lambda: float
    markets: list[MarketProbabilities]
    model_type: str
    model_version: str
    confidence: ConfidenceLevel
    features_snapshot: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "external_match_id": self.external_match_id,
            "home_lambda": round(self.home_lambda, 4),
            "away_lambda": round(self.away_lambda, 4),
            "markets": [m.to_dict() for m in self.markets],
            "model_type": self.model_type,
            "model_version": self.model_version,
            "confidence": self.confidence.value,
            "features_snapshot": self.features_snapshot,
            "metadata": self.metadata,
        }

    def get_market(self, market_code: str) -> MarketProbabilities | None:
        for market in self.markets:
            if market.market_code == market_code:
                return market
        return None

    def get_probability(self, market_code: str, selection: str) -> float | None:
        market = self.get_market(market_code)
        if market is None:
            return None
        return market.probabilities.get(selection)

    def flat_probabilities(self) -> dict[str, float]:
        """Vecteur plat des probabilités pour ML / tracking."""
        flat: dict[str, float] = {}
        for market in self.markets:
            for selection, prob in market.probabilities.items():
                flat[f"{market.market_code}_{selection}"] = round(prob, 6)
        flat["home_lambda"] = round(self.home_lambda, 4)
        flat["away_lambda"] = round(self.away_lambda, 4)
        return flat
