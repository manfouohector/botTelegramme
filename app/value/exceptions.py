"""Exceptions Value Engine / Odds API."""


class ValueEngineError(Exception):
    """Erreur générique Value Engine."""


class OddsAPIError(ValueEngineError):
    """Erreur API Odds."""

    def __init__(self, message: str, *, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class OddsAuthError(OddsAPIError):
    """Clé API invalide ou absente."""


class OddsRateLimitError(OddsAPIError):
    """Quota API dépassé."""


class OddsNotFoundError(ValueEngineError):
    """Cotes introuvables pour le match."""


class MatchNotFoundError(ValueEngineError):
    """Match introuvable."""
