"""Exceptions Prediction Engine."""


class PredictionEngineError(Exception):
    """Erreur générique du moteur de prédiction."""


class MatchNotFoundError(PredictionEngineError):
    """Match introuvable."""


class InsufficientPredictionDataError(PredictionEngineError):
    """Données insuffisantes pour produire une prédiction fiable."""
