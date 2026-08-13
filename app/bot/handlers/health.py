"""Handlers de santé / diagnostic."""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.bot.constants import BOT_VERSION
from app.bot.context import BotContext
from app.bot.middleware import get_bot_context


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Répond au ping — vérifie que le bot est actif."""
    ctx: BotContext = get_bot_context(context)
    name = ctx.settings.app_name
    await update.effective_message.reply_text(f"🏟 {name} — bot actif (v{BOT_VERSION})")


def register_health_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("ping", ping_command))
