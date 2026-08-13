"""Vérification admin bot."""

from __future__ import annotations

from app.config.settings import Settings


def is_admin(telegram_user_id: int, settings: Settings) -> bool:
    """True si l'utilisateur est l'admin configuré."""
    admin_id = settings.admin_telegram_id.strip()
    if not admin_id.isdigit():
        return False
    return telegram_user_id == int(admin_id)


def parse_admin_id(settings: Settings) -> int | None:
    admin_id = settings.admin_telegram_id.strip()
    if admin_id.isdigit():
        return int(admin_id)
    return None
