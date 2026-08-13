"""Matrice de scores Poisson."""

from __future__ import annotations

from scipy.stats import poisson


def build_score_matrix(
    home_lambda: float,
    away_lambda: float,
    *,
    max_goals: int = 6,
) -> dict[tuple[int, int], float]:
    """Construit P(home_goals, away_goals) indépendants Poisson."""
    matrix: dict[tuple[int, int], float] = {}
    for home_goals in range(max_goals + 1):
        for away_goals in range(max_goals + 1):
            matrix[(home_goals, away_goals)] = (
                poisson.pmf(home_goals, home_lambda) * poisson.pmf(away_goals, away_lambda)
            )

    total = sum(matrix.values())
    if total <= 0:
        return {(0, 0): 1.0}
    return {key: value / total for key, value in matrix.items()}
