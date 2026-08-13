"""Exceptions Context Engine."""


class ContextEngineError(Exception):
    """Erreur générique du Context Engine."""


class MatchNotFoundError(ContextEngineError):
    """Match introuvable."""


class InsufficientStandingsError(ContextEngineError):
    """Classement insuffisant pour calculer le contexte."""
