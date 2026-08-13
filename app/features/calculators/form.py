"""Calculateurs de features — forme récente."""

from app.features.records import TeamMatchRecord
from app.features.schemas import TeamFormFeatures


def _result_points(goals_scored: int, goals_conceded: int) -> tuple[int, str]:
    if goals_scored > goals_conceded:
        return 3, "W"
    if goals_scored == goals_conceded:
        return 1, "D"
    return 0, "L"


def compute_form_features(team_id: int, records: list[TeamMatchRecord]) -> TeamFormFeatures:
    """Calcule les features de forme sur une fenêtre de matchs."""
    features = TeamFormFeatures(team_id=team_id, matches_played=len(records))
    if not records:
        return features

    results: list[str] = []
    for rec in records:
        pts, res = _result_points(rec.goals_scored, rec.goals_conceded)
        features.points += pts
        features.goals_scored += rec.goals_scored
        features.goals_conceded += rec.goals_conceded
        results.append(res)

        if res == "W":
            features.wins += 1
        elif res == "D":
            features.draws += 1
        else:
            features.losses += 1

        if rec.goals_conceded == 0:
            features.clean_sheets += 1

    n = len(records)
    features.points_per_match = features.points / n
    features.goals_scored_per_match = features.goals_scored / n
    features.goals_conceded_per_match = features.goals_conceded / n
    features.goal_difference = features.goals_scored - features.goals_conceded

    features.win_streak = _count_streak(results, "W")
    features.unbeaten_streak = _count_unbeaten_streak(results)

    return features


def _count_streak(results: list[str], target: str) -> int:
    streak = 0
    for res in results:
        if res == target:
            streak += 1
        else:
            break
    return streak


def _count_unbeaten_streak(results: list[str]) -> int:
    streak = 0
    for res in results:
        if res in ("W", "D"):
            streak += 1
        else:
            break
    return streak
