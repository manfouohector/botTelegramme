"""Handlers fallback — commandes inconnues."""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, MessageHandler, ContextTypes, filters

from app.bot.messages import non_command_hint, unknown_command_message


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(unknown_command_message())


async def non_command_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(non_command_hint())


def register_fallback_handlers(application: Application) -> None:
    application.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, non_command_message),
        group=1,
    )
