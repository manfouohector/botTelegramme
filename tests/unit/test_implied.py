"""Tests unitaires — probabilités implicites."""

import pytest

from app.value.implied import (
    compute_edge,
    decimal_to_implied,
    normalize_overround,
    overround,
)


class TestImplied:
    def test_decimal_to_implied(self):
        assert decimal_to_implied(2.0) == pytest.approx(0.5)
        assert decimal_to_implied(1.70) == pytest.approx(0.588235, rel=1e-4)

    def test_invalid_odds_raises(self):
        with pytest.raises(ValueError):
            decimal_to_implied(1.0)

    def test_normalize_overround(self):
        raw = {"HOME": 0.526, "DRAW": 0.294, "AWAY": 0.238}
        assert overround(raw) == pytest.approx(1.058)
        norm = normalize_overround(raw)
        assert sum(norm.values()) == pytest.approx(1.0)

    def test_compute_edge_example(self):
        edge = compute_edge(0.68, 1 / 1.70)
        assert edge == pytest.approx(0.0918, rel=1e-2)
