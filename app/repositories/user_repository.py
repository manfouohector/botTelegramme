"""Persistance utilisateurs Telegram."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    """Accès PostgreSQL pour les utilisateurs."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return self.session.scalar(select(User).where(User.telegram_id == telegram_id))

    def get_by_username(self, username: str) -> User | None:
        clean = username.lstrip("@")
        return self.session.scalar(select(User).where(User.username == clean))

    def get_or_create(
        self,
        telegram_id: int,
        *,
        username: str | None = None,
        first_name: str | None = None,
    ) -> tuple[User, bool]:
        """Retourne (user, created). Met à jour username/first_name si changés."""
        user = self.get_by_telegram_id(telegram_id)
        if user is not None:
            changed = False
            if username is not None and user.username != username:
                user.username = username
                changed = True
            if first_name is not None and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if changed:
                self.session.flush()
            return user, False

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
        )
        self.session.add(user)
        self.session.flush()
        return user, True
