"""Schémas pour le Context Engine."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class TeamStanding:
    """Position d'une équipe au classement calculé."""

    team_id: int
    team_external_id: int
    team_name: str
    position: int
    played: int
    wins: int
    draws: int
    losses: int
    points: int
    goals_for: int
    goals_against: int
    goal_difference: int

    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "team_external_id": self.team_external_id,
            "team_name": self.team_name,
            "position": self.position,
            "played": self.played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "points": self.points,
            "goals_for": self.goals_for,
            "goals_against": self.goals_against,
            "goal_difference": self.goal_difference,
        }


@dataclass
class ContextFactorValue:
    """Facteur de contexte numérique."""

    name: str
    value: float
    source: str = "computed"
    reliability: str = "OFFICIAL"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": self.value,
            "source": self.source,
            "reliability": self.reliability,
        }


@dataclass
class MatchContext:
    """Contexte structuré d'un match."""

    match_id: int
    external_match_id: int
    scheduled_at: datetime
    as_of: datetime
    home_standing: TeamStanding | None
    away_standing: TeamStanding | None
    factors: list[ContextFactorValue] = field(default_factory=list)
    matches_remaining: int = 0
    data_quality: str = "LOW"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "external_match_id": self.external_match_id,
            "scheduled_at": self.scheduled_at.isoformat(),
            "as_of": self.as_of.isoformat(),
            "home_standing": self.home_standing.to_dict() if self.home_standing else None,
            "away_standing": self.away_standing.to_dict() if self.away_standing else None,
            "factors": [f.to_dict() for f in self.factors],
            "matches_remaining": self.matches_remaining,
            "data_quality": self.data_quality,
            "metadata": self.metadata,
        }

    def flat_features(self) -> dict[str, float | int]:
        """Vecteur plat de features contexte pour ML."""
        flat: dict[str, float | int] = {}
        for factor in self.factors:
            flat[factor.name] = factor.value
        flat["matches_remaining"] = self.matches_remaining
        if self.home_standing:
            flat["home_position"] = self.home_standing.position
            flat["home_points"] = self.home_standing.points
        if self.away_standing:
            flat["away_position"] = self.away_standing.position
            flat["away_points"] = self.away_standing.points
        return flat

    def get_factor(self, name: str) -> float | None:
        for f in self.factors:
            if f.name == name:
                return f.value
        return None
