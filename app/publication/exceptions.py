"""Exceptions publication Telegram."""


class PublicationError(Exception):
    """Erreur générique publication."""


class PublicationConfigError(PublicationError):
    """Configuration Telegram manquante ou invalide."""


class PublicationDeliveryError(PublicationError):
    """Échec envoi Telegram."""
