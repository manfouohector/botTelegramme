"""Dérivation des probabilités de marchés depuis la matrice de scores."""

from __future__ import annotations

from app.prediction.constants import (
    MARKET_1X2,
    MARKET_BTTS,
    MARKET_OU25,
    MODEL_DIXON_COLES,
    MODEL_POISSON,
    SELECTION_AWAY,
    SELECTION_DRAW,
    SELECTION_HOME,
    SELECTION_NO,
    SELECTION_OVER,
    SELECTION_UNDER,
    SELECTION_YES,
)
from app.prediction.schemas import MarketProbabilities


def derive_markets(
    matrix: dict[tuple[int, int], float],
    *,
    model_type: str,
    enabled_markets: tuple[str, ...],
) -> list[MarketProbabilities]:
    """Calcule les probabilités des marchés activés."""
    markets: list[MarketProbabilities] = []
    if MARKET_1X2 in enabled_markets:
        markets.append(_market_1x2(matrix, model_type))
    if MARKET_BTTS in enabled_markets:
        markets.append(_market_btts(matrix, model_type))
    if MARKET_OU25 in enabled_markets:
        markets.append(_market_ou25(matrix, model_type))
    return markets


def _market_1x2(matrix: dict[tuple[int, int], float], model_type: str) -> MarketProbabilities:
    home = sum(prob for (h, a), prob in matrix.items() if h > a)
    draw = sum(prob for (h, a), prob in matrix.items() if h == a)
    away = sum(prob for (h, a), prob in matrix.items() if h < a)
    probs = _normalize({SELECTION_HOME: home, SELECTION_DRAW: draw, SELECTION_AWAY: away})
    return MarketProbabilities(market_code=MARKET_1X2, probabilities=probs, model_type=model_type)


def _market_btts(matrix: dict[tuple[int, int], float], model_type: str) -> MarketProbabilities:
    yes = sum(prob for (h, a), prob in matrix.items() if h > 0 and a > 0)
    probs = _normalize({SELECTION_YES: yes, SELECTION_NO: 1.0 - yes})
    return MarketProbabilities(market_code=MARKET_BTTS, probabilities=probs, model_type=model_type)


def _market_ou25(matrix: dict[tuple[int, int], float], model_type: str) -> MarketProbabilities:
    over = sum(prob for (h, a), prob in matrix.items() if h + a > 2)
    probs = _normalize({SELECTION_OVER: over, SELECTION_UNDER: 1.0 - over})
    return MarketProbabilities(market_code=MARKET_OU25, probabilities=probs, model_type=model_type)


def ensemble_1x2(
    poisson_probs: dict[str, float],
    ml_probs: dict[str, float] | None,
    *,
    poisson_weight: float,
) -> dict[str, float]:
    """Combine Poisson/Dixon-Coles et ML pour le 1X2."""
    if not ml_probs:
        return poisson_probs
    weight = min(max(poisson_weight, 0.0), 1.0)
    combined = {}
    for key in (SELECTION_HOME, SELECTION_DRAW, SELECTION_AWAY):
        combined[key] = weight * poisson_probs.get(key, 0.0) + (1 - weight) * ml_probs.get(key, 0.0)
    return _normalize(combined)


def _normalize(probs: dict[str, float]) -> dict[str, float]:
    total = sum(probs.values())
    if total <= 0:
        n = len(probs)
        return {key: 1.0 / n for key in probs}
    return {key: value / total for key, value in probs.items()}


def poisson_model_label(*, dixon_coles_enabled: bool) -> str:
    return MODEL_DIXON_COLES if dixon_coles_enabled else MODEL_POISSON
