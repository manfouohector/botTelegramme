"""Exceptions Feature Engineering."""


class FeatureEngineError(Exception):
    """Erreur générique du Feature Engine."""


class MatchNotFoundError(FeatureEngineError):
    """Match introuvable en base."""


class InsufficientDataError(FeatureEngineError):
    """Données historiques insuffisantes pour calculer les features."""
