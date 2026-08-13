"""Calcul des facteurs de contexte numériques."""

from __future__ import annotations

from app.config.settings import Settings
from app.context.schemas import ContextFactorValue, TeamStanding
from app.context.standings import StandingsSnapshot, _TeamAccumulator


def _to_standing(acc: _TeamAccumulator, position: int) -> TeamStanding:
    return TeamStanding(
        team_id=acc.team_id,
        team_external_id=acc.team_external_id,
        team_name=acc.team_name,
        position=position,
        played=acc.played,
        wins=acc.wins,
        draws=acc.draws,
        losses=acc.losses,
        points=acc.points,
        goals_for=acc.goals_for,
        goals_against=acc.goals_against,
        goal_difference=acc.goals_for - acc.goals_against,
    )


def build_standings_map(snapshot: StandingsSnapshot) -> dict[int, TeamStanding]:
    result: dict[int, TeamStanding] = {}
    for pos, acc in enumerate(snapshot.sorted_by_rank(), start=1):
        result[acc.team_id] = _to_standing(acc, pos)
    return result


def compute_context_factors(
    *,
    home_standing: TeamStanding | None,
    away_standing: TeamStanding | None,
    total_teams: int,
    matches_remaining: int,
    is_derby: bool,
    is_cup: bool,
    settings: Settings,
    leader_points: int | None = None,
) -> list[ContextFactorValue]:
    """Calcule les facteurs de contexte à partir du classement."""
    factors: list[ContextFactorValue] = []

    factors.append(ContextFactorValue("matches_remaining", float(matches_remaining)))
    factors.append(ContextFactorValue("derby", 1.0 if is_derby else 0.0))
    factors.append(ContextFactorValue("cup_match", 1.0 if is_cup else 0.0))

    if home_standing is None or away_standing is None or total_teams == 0:
        factors.append(ContextFactorValue("data_available", 0.0))
        if is_derby or is_cup:
            factors.append(ContextFactorValue("high_stakes", 1.0))
        return factors

    factors.append(ContextFactorValue("data_available", 1.0))
    factors.append(ContextFactorValue("home_position", float(home_standing.position)))
    factors.append(ContextFactorValue("away_position", float(away_standing.position)))
    factors.append(ContextFactorValue("home_points", float(home_standing.points)))
    factors.append(ContextFactorValue("away_points", float(away_standing.points)))
    factors.append(ContextFactorValue("points_gap", float(home_standing.points - away_standing.points)))

    relegation_cutoff = total_teams - settings.context_relegation_positions + 1

    home_title = 1.0 if home_standing.position <= settings.context_title_race_positions else 0.0
    away_title = 1.0 if away_standing.position <= settings.context_title_race_positions else 0.0
    home_relegation = 1.0 if home_standing.position >= relegation_cutoff else 0.0
    away_relegation = 1.0 if away_standing.position >= relegation_cutoff else 0.0
    home_european = 1.0 if home_standing.position <= settings.context_european_positions else 0.0
    away_european = 1.0 if away_standing.position <= settings.context_european_positions else 0.0

    factors.extend([
        ContextFactorValue("home_title_race", home_title),
        ContextFactorValue("away_title_race", away_title),
        ContextFactorValue("title_race", max(home_title, away_title)),
        ContextFactorValue("home_relegation_battle", home_relegation),
        ContextFactorValue("away_relegation_battle", away_relegation),
        ContextFactorValue("relegation_battle", max(home_relegation, away_relegation)),
        ContextFactorValue("home_european_race", home_european),
        ContextFactorValue("away_european_race", away_european),
        ContextFactorValue("european_race", max(home_european, away_european)),
    ])

    if leader_points is not None:
        factors.append(ContextFactorValue("leader_points", float(leader_points)))
        factors.append(ContextFactorValue("home_gap_to_leader", float(leader_points - home_standing.points)))
        factors.append(ContextFactorValue("away_gap_to_leader", float(leader_points - away_standing.points)))

    factors.append(ContextFactorValue(
        "home_gap_to_relegation_zone",
        float(max(0, relegation_cutoff - home_standing.position)),
    ))
    factors.append(ContextFactorValue(
        "away_gap_to_relegation_zone",
        float(max(0, away_standing.position - relegation_cutoff + 1)) if away_relegation else 0.0,
    ))

    high_stakes = _compute_high_stakes(
        home_standing, away_standing,
        home_title, away_title,
        home_relegation, away_relegation,
        home_european, away_european,
        is_derby, is_cup,
        settings.context_high_stakes_points_gap,
    )
    factors.append(ContextFactorValue("high_stakes", high_stakes))

    importance = (
        high_stakes * 3
        + max(home_title, away_title) * 2
        + max(home_relegation, away_relegation) * 2
        + (1.0 if is_derby else 0.0) * 1.5
        + (1.0 if is_cup else 0.0)
    )
    factors.append(ContextFactorValue("match_importance", min(importance, 10.0)))

    return factors


def get_leader_points(snapshot: StandingsSnapshot) -> int | None:
    ranked = snapshot.sorted_by_rank()
    return ranked[0].points if ranked else None


def _compute_high_stakes(
    home: TeamStanding,
    away: TeamStanding,
    home_title: float,
    away_title: float,
    home_relegation: float,
    away_relegation: float,
    home_european: float,
    away_european: float,
    is_derby: bool,
    is_cup: bool,
    points_gap_threshold: int,
) -> float:
    if is_derby or is_cup:
        return 1.0
    if home_title or away_title:
        return 1.0
    if home_relegation or away_relegation:
        return 1.0
    if home_european or away_european:
        if abs(home.points - away.points) <= points_gap_threshold:
            return 1.0
    if abs(home.position - away.position) >= 10 and (home_relegation or away_title or home_title or away_relegation):
        return 1.0
    return 0.0


def assess_context_quality(
    home_standing: TeamStanding | None,
    away_standing: TeamStanding | None,
    min_played: int = 3,
) -> str:
    if home_standing is None or away_standing is None:
        return "LOW"
    if home_standing.played >= min_played and away_standing.played >= min_played:
        return "HIGH"
    if home_standing.played >= 1 and away_standing.played >= 1:
        return "MEDIUM"
    return "LOW"
