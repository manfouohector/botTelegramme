"""Schémas de features pour le Prediction Engine."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TeamFormFeatures:
    """Features de forme récente d'une équipe."""

    team_id: int
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: int = 0
    points_per_match: float = 0.0
    goals_scored: int = 0
    goals_conceded: int = 0
    goals_scored_per_match: float = 0.0
    goals_conceded_per_match: float = 0.0
    goal_difference: int = 0
    win_streak: int = 0
    unbeaten_streak: int = 0
    clean_sheets: int = 0

    def to_dict(self) -> dict:
        return {
            "matches_played": self.matches_played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "points": self.points,
            "points_per_match": round(self.points_per_match, 4),
            "goals_scored": self.goals_scored,
            "goals_conceded": self.goals_conceded,
            "goals_scored_per_match": round(self.goals_scored_per_match, 4),
            "goals_conceded_per_match": round(self.goals_conceded_per_match, 4),
            "goal_difference": self.goal_difference,
            "win_streak": self.win_streak,
            "unbeaten_streak": self.unbeaten_streak,
            "clean_sheets": self.clean_sheets,
        }


@dataclass
class HomeAwayFeatures:
    """Performance domicile ou extérieur."""

    venue: str  # "home" ou "away"
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points_per_match: float = 0.0
    goals_scored_per_match: float = 0.0
    goals_conceded_per_match: float = 0.0

    def to_dict(self) -> dict:
        return {
            "venue": self.venue,
            "matches_played": self.matches_played,
            "wins": self.wins,
            "draws": self.draws,
            "losses": self.losses,
            "points_per_match": round(self.points_per_match, 4),
            "goals_scored_per_match": round(self.goals_scored_per_match, 4),
            "goals_conceded_per_match": round(self.goals_conceded_per_match, 4),
        }


@dataclass
class AttackDefenseFeatures:
    """Features attaque / défense agrégées."""

    goals_scored_per_match: float = 0.0
    goals_conceded_per_match: float = 0.0
    shots_per_match: float | None = None
    shots_on_target_per_match: float | None = None
    stats_available: bool = False

    def to_dict(self) -> dict:
        result = {
            "goals_scored_per_match": round(self.goals_scored_per_match, 4),
            "goals_conceded_per_match": round(self.goals_conceded_per_match, 4),
            "stats_available": self.stats_available,
        }
        if self.shots_per_match is not None:
            result["shots_per_match"] = round(self.shots_per_match, 4)
        if self.shots_on_target_per_match is not None:
            result["shots_on_target_per_match"] = round(self.shots_on_target_per_match, 4)
        return result


@dataclass
class H2HFeatures:
    """Confrontations directes (poids limité)."""

    matches_played: int = 0
    home_wins: int = 0
    draws: int = 0
    away_wins: int = 0
    avg_total_goals: float = 0.0

    def to_dict(self) -> dict:
        return {
            "matches_played": self.matches_played,
            "home_wins": self.home_wins,
            "draws": self.draws,
            "away_wins": self.away_wins,
            "avg_total_goals": round(self.avg_total_goals, 4),
        }


@dataclass
class MatchFeatures:
    """Ensemble complet de features pour un match."""

    match_id: int
    external_match_id: int
    home_team_id: int
    away_team_id: int
    scheduled_at: datetime
    as_of: datetime
    home_form: TeamFormFeatures
    away_form: TeamFormFeatures
    home_at_home: HomeAwayFeatures
    away_at_away: HomeAwayFeatures
    home_attack_defense: AttackDefenseFeatures
    away_attack_defense: AttackDefenseFeatures
    h2h: H2HFeatures
    data_quality: str = "LOW"
    matches_used_home: int = 0
    matches_used_away: int = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "external_match_id": self.external_match_id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "scheduled_at": self.scheduled_at.isoformat(),
            "as_of": self.as_of.isoformat(),
            "home_form": self.home_form.to_dict(),
            "away_form": self.away_form.to_dict(),
            "home_at_home": self.home_at_home.to_dict(),
            "away_at_away": self.away_at_away.to_dict(),
            "home_attack_defense": self.home_attack_defense.to_dict(),
            "away_attack_defense": self.away_attack_defense.to_dict(),
            "h2h": self.h2h.to_dict(),
            "data_quality": self.data_quality,
            "matches_used_home": self.matches_used_home,
            "matches_used_away": self.matches_used_away,
            "metadata": self.metadata,
        }

    def flat_features(self) -> dict[str, float | int | bool]:
        """Vecteur plat pour ML — préfixé par côté."""
        flat: dict[str, float | int | bool] = {}
        for key, value in self.home_form.to_dict().items():
            if key != "matches_played":
                flat[f"home_form_{key}"] = value
        for key, value in self.away_form.to_dict().items():
            if key != "matches_played":
                flat[f"away_form_{key}"] = value
        for key, value in self.home_at_home.to_dict().items():
            if key not in ("venue", "matches_played"):
                flat[f"home_venue_{key}"] = value
        for key, value in self.away_at_away.to_dict().items():
            if key not in ("venue", "matches_played"):
                flat[f"away_venue_{key}"] = value
        for key, value in self.home_attack_defense.to_dict().items():
            if key != "stats_available":
                flat[f"home_ad_{key}"] = value
        for key, value in self.away_attack_defense.to_dict().items():
            if key != "stats_available":
                flat[f"away_ad_{key}"] = value
        for key, value in self.h2h.to_dict().items():
            flat[f"h2h_{key}"] = value
        flat["matches_used_home"] = self.matches_used_home
        flat["matches_used_away"] = self.matches_used_away
        return flat
