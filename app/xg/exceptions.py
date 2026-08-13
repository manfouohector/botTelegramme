"""Exceptions xG Engine."""


class XGEngineError(Exception):
    """Erreur générique xG."""


class MatchNotFoundError(XGEngineError):
    """Match introuvable."""


class InsufficientXGDataError(XGEngineError):
    """Données insuffisantes pour estimer le xG."""
