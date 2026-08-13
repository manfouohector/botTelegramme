"""Résolution des résultats réels par marché."""

from __future__ import annotations

from app.prediction.constants import (
    MARKET_1X2,
    MARKET_BTTS,
    MARKET_OU25,
    SELECTION_AWAY,
    SELECTION_DRAW,
    SELECTION_HOME,
    SELECTION_NO,
    SELECTION_OVER,
    SELECTION_UNDER,
    SELECTION_YES,
)
from app.tracking.exceptions import TrackingError


def resolve_market_outcome(market_code: str, home_score: int, away_score: int) -> str:
    """Retourne la sélection gagnante pour un marché donné."""
    outcomes = resolve_all_outcomes(home_score, away_score)
    try:
        return outcomes[market_code.upper()]
    except KeyError as exc:
        raise TrackingError(f"Marché non supporté : {market_code}") from exc


def resolve_all_outcomes(home_score: int, away_score: int) -> dict[str, str]:
    """Retourne les résultats pour tous les marchés MVP."""
    total = home_score + away_score
    btts = home_score > 0 and away_score > 0

    if home_score > away_score:
        result_1x2 = SELECTION_HOME
    elif home_score < away_score:
        result_1x2 = SELECTION_AWAY
    else:
        result_1x2 = SELECTION_DRAW

    return {
        MARKET_1X2: result_1x2,
        MARKET_BTTS: SELECTION_YES if btts else SELECTION_NO,
        MARKET_OU25: SELECTION_OVER if total > 2 else SELECTION_UNDER,
    }
