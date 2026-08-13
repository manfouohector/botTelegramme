"""Middleware bot — session DB et tracking utilisateur."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.context import BotContext
from app.bot.services.user_service import ensure_user
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


def get_bot_context(context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    """Récupère le contexte applicatif depuis bot_data."""
    return context.application.bot_data["ctx"]


async def user_tracking_middleware(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Enregistre/met à jour l'utilisateur à chaque interaction."""
    telegram_user = update.effective_user
    if telegram_user is None:
        return

    ctx = get_bot_context(context)
    session = ctx.session_factory()
    try:
        user, created = ensure_user(session, telegram_user)
        session.commit()
        if created:
            log_event(logger, "BOT_USER_REGISTERED", telegram_id=user.telegram_id)
    except Exception:
        session.rollback()
        logger.exception("BOT_USER_TRACKING_FAILED | telegram_id=%s", telegram_user.id)
    finally:
        session.close()
