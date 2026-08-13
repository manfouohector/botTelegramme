"""Exceptions Premium."""


class PremiumError(Exception):
    """Erreur générique Premium."""


class UserNotFoundError(PremiumError):
    """Utilisateur Telegram introuvable."""


class ActivationError(PremiumError):
    """Échec activation abonnement."""
