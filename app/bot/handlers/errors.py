"""Gestion globale des erreurs bot."""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, ContextTypes

from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log les erreurs et informe l'utilisateur si possible."""
    log_event(
        logger,
        "BOT_HANDLER_ERROR",
        error=str(context.error),
        update_type=type(update).__name__,
    )
    logger.exception("Unhandled bot exception", exc_info=context.error)

    if isinstance(update, Update) and update.effective_message is not None:
        try:
            await update.effective_message.reply_text(
                "Une erreur est survenue. Réessayez dans quelques instants."
            )
        except Exception:
            logger.exception("BOT_ERROR_REPLY_FAILED")


def register_error_handler(application: Application) -> None:
    application.add_error_handler(error_handler)
