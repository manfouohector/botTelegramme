"""Commandes utilisateur — /start, /free, /premium."""

from __future__ import annotations

# pyrefly: ignore [missing-import]
from telegram import Message, Update
# pyrefly: ignore [missing-import]
from telegram.constants import ParseMode
# pyrefly: ignore [missing-import]
from telegram.ext import Application, CommandHandler, ContextTypes

from app.bot.keyboards import free_keyboard, premium_keyboard, start_keyboard
from app.bot.messages import free_message, premium_message, start_message
from app.bot.middleware import get_bot_context
from app.bot.utils.links import build_telegram_channel_link, build_whatsapp_link
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_start(update.effective_message, context)


async def free_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_free(update.effective_message, context)


async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_premium(update, context)


async def _send_start(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_bot_context(context).settings
    await message.reply_text(
        start_message(settings),
        reply_markup=start_keyboard(settings),
        parse_mode=ParseMode.HTML,
    )
    log_event(logger, "BOT_CMD_START", chat_id=message.chat_id)


async def _send_free(message: Message, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_bot_context(context).settings
    link = build_telegram_channel_link(settings.telegram_free_channel_id)
    await message.reply_text(
        free_message(settings, channel_link=link),
        reply_markup=free_keyboard(settings),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False,
    )
    log_event(logger, "BOT_CMD_FREE", chat_id=message.chat_id, has_link=bool(link))


async def _send_premium(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    bot_ctx = get_bot_context(context)
    settings = bot_ctx.settings
    user = update.effective_user
    telegram_id = user.id if user else message.chat_id
    username = user.username if user else None

    premium_active = False
    premium_until = None
    session = bot_ctx.session_factory()
    try:
        from app.services.premium_service import PremiumService

        status = PremiumService(session, settings).get_status(telegram_id)
        if status.is_premium and status.date_fin:
            premium_active = True
            premium_until = status.date_fin.strftime("%d/%m/%Y")
    finally:
        session.close()

    whatsapp_link = None if premium_active else build_whatsapp_link(
        settings.whatsapp_phone,
        telegram_id=telegram_id,
        username=username,
    )
    await message.reply_text(
        premium_message(
            settings,
            whatsapp_link=whatsapp_link,
            premium_active=premium_active,
            premium_until=premium_until,
        ),
        reply_markup=None if premium_active else premium_keyboard(
            settings,
            telegram_id=telegram_id,
            username=username,
        ),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )
    log_event(
        logger,
        "BOT_CMD_PREMIUM",
        chat_id=message.chat_id,
        has_whatsapp=bool(whatsapp_link),
    )


def register_command_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("free", free_command))
    application.add_handler(CommandHandler("premium", premium_command))
