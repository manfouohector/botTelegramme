"""Calculateurs de features — domicile / extérieur."""

from app.features.schemas import HomeAwayFeatures
from app.features.calculators.form import _result_points
from app.features.records import TeamMatchRecord


def compute_home_away_features(
    team_id: int,
    records: list[TeamMatchRecord],
    venue: str,
) -> HomeAwayFeatures:
    """Calcule la performance domicile ou extérieur."""
    features = HomeAwayFeatures(venue=venue, matches_played=len(records))
    if not records:
        return features

    total_points = 0
    total_scored = 0
    total_conceded = 0

    for rec in records:
        pts, res = _result_points(rec.goals_scored, rec.goals_conceded)
        total_points += pts
        total_scored += rec.goals_scored
        total_conceded += rec.goals_conceded

        if res == "W":
            features.wins += 1
        elif res == "D":
            features.draws += 1
        else:
            features.losses += 1

    n = len(records)
    features.points_per_match = total_points / n
    features.goals_scored_per_match = total_scored / n
    features.goals_conceded_per_match = total_conceded / n

    return features
