"""Tests unitaires — Poisson score matrix."""

from app.prediction.poisson import build_score_matrix


class TestPoissonMatrix:
    def test_sums_to_one(self):
        matrix = build_score_matrix(1.5, 1.1, max_goals=6)
        assert abs(sum(matrix.values()) - 1.0) < 1e-9

    def test_home_favorite_higher_win_mass(self):
        matrix = build_score_matrix(2.0, 0.8, max_goals=6)
        home_win = sum(p for (h, a), p in matrix.items() if h > a)
        away_win = sum(p for (h, a), p in matrix.items() if h < a)
        assert home_win > away_win

    def test_symmetric_lambdas_near_draw(self):
        matrix = build_score_matrix(1.3, 1.3, max_goals=6)
        home = sum(p for (h, a), p in matrix.items() if h > a)
        away = sum(p for (h, a), p in matrix.items() if h < a)
        assert abs(home - away) < 0.05
