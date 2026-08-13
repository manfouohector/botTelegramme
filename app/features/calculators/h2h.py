"""Calculateurs de features — confrontations directes (H2H)."""

from app.features.schemas import H2HFeatures
from app.models.match import Match


def compute_h2h_features(
    matches: list[Match],
    perspective_home_team_id: int,
    perspective_away_team_id: int,
) -> H2HFeatures:
    """
    Calcule le H2H du point de vue du match à prédire.

    home_wins = victoires de perspective_home_team_id (peu importe le lieu du H2H).
    """
    features = H2HFeatures(matches_played=len(matches))
    if not matches:
        return features

    total_goals = 0
    for match in matches:
        total_goals += (match.home_score or 0) + (match.away_score or 0)

        if match.home_team_id == perspective_home_team_id:
            hs, aws = match.home_score or 0, match.away_score or 0
        elif match.away_team_id == perspective_home_team_id:
            hs, aws = match.away_score or 0, match.home_score or 0
        else:
            continue

        if hs > aws:
            features.home_wins += 1
        elif hs == aws:
            features.draws += 1
        else:
            features.away_wins += 1

    features.avg_total_goals = total_goals / len(matches)
    return features
