"""Service utilisateur pour le bot."""

from __future__ import annotations

from telegram import User as TelegramUser

from app.models.user import User
from app.repositories.user_repository import UserRepository


def ensure_user(session, telegram_user: TelegramUser) -> tuple[User, bool]:
    """Crée ou met à jour l'utilisateur depuis un profil Telegram."""
    repo = UserRepository(session)
    username = telegram_user.username
    return repo.get_or_create(
        telegram_user.id,
        username=username,
        first_name=telegram_user.first_name,
    )
