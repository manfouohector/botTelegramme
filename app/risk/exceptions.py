"""Exceptions Risk Engine."""


class RiskEngineError(Exception):
    """Erreur générique Risk Engine."""


class MatchNotFoundError(RiskEngineError):
    """Match introuvable."""
