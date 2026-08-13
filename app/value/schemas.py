"""Schémas Value Engine."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class NormalizedOdd:
    """Cote normalisée depuis The Odds API."""

    external_event_id: str
    sport_key: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker: str
    market_code: str
    selection: str
    decimal_odds: float
    point: float | None = None

    def to_dict(self) -> dict:
        return {
            "external_event_id": self.external_event_id,
            "sport_key": self.sport_key,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "commence_time": self.commence_time.isoformat(),
            "bookmaker": self.bookmaker,
            "market_code": self.market_code,
            "selection": self.selection,
            "decimal_odds": round(self.decimal_odds, 4),
            "point": self.point,
        }


@dataclass
class ValueOpportunity:
    """Opportunité de value détectée."""

    match_id: int
    market_code: str
    selection: str
    model_probability: float
    implied_probability_raw: float
    implied_probability: float
    decimal_odds: float
    value_edge: float
    bookmaker: str
    is_value: bool
    overround_normalized: bool = False

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "market_code": self.market_code,
            "selection": self.selection,
            "model_probability": round(self.model_probability, 6),
            "implied_probability_raw": round(self.implied_probability_raw, 6),
            "implied_probability": round(self.implied_probability, 6),
            "decimal_odds": round(self.decimal_odds, 4),
            "value_edge": round(self.value_edge, 6),
            "bookmaker": self.bookmaker,
            "is_value": self.is_value,
            "overround_normalized": self.overround_normalized,
        }


@dataclass
class MatchValueAnalysis:
    """Analyse value complète pour un match."""

    match_id: int
    opportunities: list[ValueOpportunity] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def best_value(self) -> ValueOpportunity | None:
        values = [o for o in self.opportunities if o.is_value]
        if not values:
            return None
        return max(values, key=lambda o: o.value_edge)

    @property
    def has_value(self) -> bool:
        return any(o.is_value for o in self.opportunities)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "has_value": self.has_value,
            "best_value": self.best_value.to_dict() if self.best_value else None,
            "opportunities": [o.to_dict() for o in self.opportunities],
            "metadata": self.metadata,
        }
