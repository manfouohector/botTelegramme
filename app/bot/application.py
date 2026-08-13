"""Factory Application python-telegram-bot."""

from __future__ import annotations

from telegram.ext import Application

from app.bot.context import BotContext
from app.bot.exceptions import BotNotConfiguredError
from app.bot.handlers import register_handlers
from app.config.settings import Settings, get_settings
from app.database.session import get_session_factory
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


def create_application(settings: Settings | None = None) -> Application:
    """Construit l'Application PTB prête pour polling ou webhook."""
    cfg = settings or get_settings()
    if not cfg.has_telegram():
        raise BotNotConfiguredError(
            "TELEGRAM_BOT_TOKEN non configuré. Renseignez la variable dans .env."
        )

    application = (
        Application.builder()
        .token(cfg.telegram_bot_token.strip())
        .connect_timeout(cfg.telegram_request_timeout)
        .read_timeout(cfg.telegram_request_timeout)
        .write_timeout(cfg.telegram_request_timeout)
        .build()
    )

    session_factory = get_session_factory(cfg)
    application.bot_data["ctx"] = BotContext(settings=cfg, session_factory=session_factory)
    register_handlers(application)

    log_event(logger, "BOT_APPLICATION_CREATED", mode=cfg.telegram_bot_mode)
    return application
