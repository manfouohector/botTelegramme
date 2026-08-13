"""Démarrage polling / webhook du bot."""

from __future__ import annotations

from telegram.ext import Application

from app.bot.application import create_application
from app.bot.exceptions import BotNotConfiguredError, BotStartupError
from app.config.settings import Settings, get_settings
from app.utils.logging import get_logger, log_event, setup_logging

logger = get_logger(__name__)


def run_bot(settings: Settings | None = None) -> None:
    """Point d'entrée synchrone — polling ou webhook selon config."""
    cfg = settings or get_settings()
    setup_logging(cfg)

    if not cfg.has_telegram():
        raise BotNotConfiguredError(
            "TELEGRAM_BOT_TOKEN non configuré. Impossible de démarrer le bot."
        )

    if cfg.telegram_bot_mode == "webhook" and not cfg.telegram_webhook_url.strip():
        raise BotNotConfiguredError(
            "TELEGRAM_WEBHOOK_URL requis en mode webhook."
        )

    application = create_application(cfg)
    log_event(logger, "BOT_STARTING", mode=cfg.telegram_bot_mode)

    try:
        if cfg.telegram_bot_mode == "webhook":
            _run_webhook(application, cfg)
        else:
            application.run_polling(drop_pending_updates=cfg.telegram_drop_pending_updates)
    except BotNotConfiguredError:
        raise
    except Exception as exc:
        raise BotStartupError(f"Échec démarrage bot : {exc}") from exc


def _run_webhook(application: Application, settings: Settings) -> None:
    application.run_webhook(
        listen="0.0.0.0",
        port=settings.telegram_webhook_port,
        url_path=settings.telegram_webhook_path,
        webhook_url=settings.telegram_webhook_url.strip(),
        drop_pending_updates=settings.telegram_drop_pending_updates,
    )
