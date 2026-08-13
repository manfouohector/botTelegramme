"""Probabilités implicites et normalisation de marge bookmaker."""

from __future__ import annotations


def decimal_to_implied(decimal_odds: float) -> float:
    """Probabilité implicite brute : 1 / cote."""
    if decimal_odds <= 1.0:
        raise ValueError(f"Cote décimale invalide : {decimal_odds}")
    return 1.0 / decimal_odds


def normalize_overround(implied_probs: dict[str, float]) -> dict[str, float]:
    """
    Retire la marge bookmaker (overround) en renormalisant.

    Si les probabilités implicites brutes somment à > 1, on normalise à 1.
    """
    total = sum(implied_probs.values())
    if total <= 0:
        return dict(implied_probs)
    return {key: prob / total for key, prob in implied_probs.items()}


def compute_edge(model_probability: float, market_probability: float) -> float:
    """Edge = probabilité modèle − probabilité marché."""
    return model_probability - market_probability


def overround(implied_probs: dict[str, float]) -> float:
    """Overround total (ex. 1.05 = 5% marge)."""
    return sum(implied_probs.values())
