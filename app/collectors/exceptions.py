"""Exceptions spécifiques au Data Collector."""


class CollectorError(Exception):
    """Erreur générique du collecteur."""


class SportmonksAPIError(CollectorError):
    """Erreur retournée par l'API Sportmonks."""

    def __init__(self, message: str, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class SportmonksAuthError(SportmonksAPIError):
    """Token invalide ou non autorisé."""


class SportmonksRateLimitError(SportmonksAPIError):
    """Quota API dépassé."""


class SportmonksTimeoutError(SportmonksAPIError):
    """Timeout lors de l'appel API."""


class SportmonksEmptyResponseError(SportmonksAPIError):
    """Réponse vide ou JSON invalide."""


class NormalizationError(CollectorError):
    """Impossible de normaliser une réponse API."""


class CollectorConfigError(CollectorError):
    """Configuration manquante ou invalide."""
