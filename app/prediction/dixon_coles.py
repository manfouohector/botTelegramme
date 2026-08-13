"""Ajustement Dixon-Coles pour les scores faibles."""

from __future__ import annotations


def dixon_coles_tau(
    home_goals: int,
    away_goals: int,
    home_lambda: float,
    away_lambda: float,
    rho: float,
) -> float:
    """Facteur tau(x,y) Dixon-Coles."""
    if home_goals == 0 and away_goals == 0:
        return 1.0 - home_lambda * away_lambda * rho
    if home_goals == 0 and away_goals == 1:
        return 1.0 + home_lambda * rho
    if home_goals == 1 and away_goals == 0:
        return 1.0 + away_lambda * rho
    if home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    return 1.0


def apply_dixon_coles(
    matrix: dict[tuple[int, int], float],
    home_lambda: float,
    away_lambda: float,
    rho: float,
) -> dict[tuple[int, int], float]:
    """Applique la correction Dixon-Coles et renormalise."""
    adjusted = {
        score: prob * dixon_coles_tau(score[0], score[1], home_lambda, away_lambda, rho)
        for score, prob in matrix.items()
    }
    total = sum(adjusted.values())
    if total <= 0:
        return matrix
    return {score: prob / total for score, prob in adjusted.items()}
