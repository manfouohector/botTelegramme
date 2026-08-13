"""Job expiration abonnements Premium."""

from __future__ import annotations

import asyncio

from telegram import Bot

from app.config.settings import Settings, get_settings
from app.database.session import session_scope
from app.services.expiration_service import SubscriptionExpirationService
from app.utils.logging import get_logger, log_event, setup_logging

logger = get_logger(__name__)


async def run_subscription_expiration_async(
    settings: Settings | None = None,
    *,
    notify: bool = True,
) -> dict:
    """Exécute l'expiration avec actions Telegram si token configuré."""
    cfg = settings or get_settings()
    setup_logging(cfg)

    with session_scope(cfg) as session:
        service = SubscriptionExpirationService(session, cfg)
        bot = Bot(cfg.telegram_bot_token.strip()) if cfg.has_telegram() else None
        result = await service.process_expirations(
            bot,
            notify_users=notify and bot is not None,
        )
        return result.to_dict()


def run_subscription_expiration(
    settings: Settings | None = None,
    *,
    notify: bool = True,
) -> dict:
    """Point d'entrée synchrone pour cron / CLI."""
    return asyncio.run(run_subscription_expiration_async(settings, notify=notify))
