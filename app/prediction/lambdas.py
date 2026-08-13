"""Estimation des lambdas (buts attendus) pour Poisson."""

from __future__ import annotations

from app.config.settings import Settings
from app.features.schemas import MatchFeatures
from app.xg.constants import MODEL_UNAVAILABLE
from app.xg.schemas import MatchXG


def estimate_lambdas(
    features: MatchFeatures,
    xg: MatchXG | None,
    settings: Settings,
) -> tuple[float, float]:
    """
    Estime home_lambda / away_lambda depuis forme + xG proxy si disponible.

    Formule type Poisson football : attaque équipe × défense adversaire / moyenne ligue.
    """
    home_scored = _venue_goals_scored(features.home_at_home, features.home_form)
    home_conceded = _venue_goals_conceded(features.home_at_home, features.home_form)
    away_scored = _venue_goals_scored(features.away_at_away, features.away_form)
    away_conceded = _venue_goals_conceded(features.away_at_away, features.away_form)

    league_home = settings.prediction_league_avg_home_goals
    league_away = settings.prediction_league_avg_away_goals
    home_adv = settings.prediction_home_advantage

    if home_scored > 0 and away_conceded > 0:
        home_lambda = (home_scored * away_conceded / league_away) * home_adv
    else:
        home_lambda = league_home * home_adv

    if away_scored > 0 and home_conceded > 0:
        away_lambda = away_scored * home_conceded / league_home
    else:
        away_lambda = league_away

    if xg is not None and xg.model_type != MODEL_UNAVAILABLE:
        if xg.home_xg is not None and xg.away_xg is not None:
            weight = settings.prediction_xg_blend_weight
            home_lambda = weight * xg.home_xg + (1 - weight) * home_lambda
            away_lambda = weight * xg.away_xg + (1 - weight) * away_lambda

    return max(0.05, home_lambda), max(0.05, away_lambda)


def _venue_goals_scored(venue, form) -> float:
    if venue.matches_played > 0:
        return venue.goals_scored_per_match
    return form.goals_scored_per_match


def _venue_goals_conceded(venue, form) -> float:
    if venue.matches_played > 0:
        return venue.goals_conceded_per_match
    return form.goals_conceded_per_match
