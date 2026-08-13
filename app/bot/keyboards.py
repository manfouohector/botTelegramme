"""Claviers inline Telegram."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.utils.links import build_telegram_channel_link, build_whatsapp_link
from app.config.settings import Settings

CALLBACK_FREE = "cmd:free"
CALLBACK_PREMIUM = "cmd:premium"


def start_keyboard(settings: Settings) -> InlineKeyboardMarkup:
    """Boutons accueil : Canal Gratuit + Premium."""
    free_link = build_telegram_channel_link(settings.telegram_free_channel_id)
    if free_link:
        free_btn = InlineKeyboardButton("🟢 Canal Gratuit", url=free_link)
    else:
        free_btn = InlineKeyboardButton("🟢 Canal Gratuit", callback_data=CALLBACK_FREE)

    return InlineKeyboardMarkup(
        [
            [free_btn],
            [InlineKeyboardButton("👑 Premium", callback_data=CALLBACK_PREMIUM)],
        ]
    )


def free_keyboard(settings: Settings) -> InlineKeyboardMarkup | None:
    free_link = build_telegram_channel_link(settings.telegram_free_channel_id)
    if not free_link:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🟢 Rejoindre le canal", url=free_link)]]
    )


def premium_keyboard(
    settings: Settings,
    *,
    telegram_id: int,
    username: str | None,
) -> InlineKeyboardMarkup | None:
    whatsapp_link = build_whatsapp_link(
        settings.whatsapp_phone,
        telegram_id=telegram_id,
        username=username,
    )
    if not whatsapp_link:
        return None
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("📲 Contacter via WhatsApp", url=whatsapp_link)]]
    )
