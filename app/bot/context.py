"""Contexte partagé du bot Telegram."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import Settings


@dataclass
class BotContext:
    """Services injectés dans application.bot_data."""

    settings: Settings
    session_factory: sessionmaker[Session]
