"""Callbacks des boutons inline."""

from __future__ import annotations

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from app.bot.handlers.commands import _send_free, _send_premium, _send_start
from app.bot.keyboards import CALLBACK_FREE, CALLBACK_PREMIUM


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or query.message is None:
        return

    await query.answer()

    if query.data == CALLBACK_FREE:
        await _send_free(query.message, context)
    elif query.data == CALLBACK_PREMIUM:
        await _send_premium(update, context)
    elif query.data == "cmd:start":
        await _send_start(query.message, context)


def register_callback_handlers(application: Application) -> None:
    application.add_handler(
        CallbackQueryHandler(menu_callback, pattern=f"^({CALLBACK_FREE}|{CALLBACK_PREMIUM})$")
    )
