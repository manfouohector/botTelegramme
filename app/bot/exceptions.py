"""Exceptions Bot Telegram."""


class BotError(Exception):
    """Erreur générique bot."""


class BotNotConfiguredError(BotError):
    """Token Telegram ou configuration manquante."""


class BotStartupError(BotError):
    """Échec au démarrage du bot."""
