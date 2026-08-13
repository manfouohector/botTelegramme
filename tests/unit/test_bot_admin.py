"""Tests unitaires — commande admin /activate."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from telegram import Chat, Message, Update, User

from app.bot.context import BotContext
from app.bot.handlers.admin import activate_command
from app.config.settings import Settings
from app.database.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User as DbUser
from app.premium.schemas import GroupInviteResult


@pytest.fixture
def admin_settings():
    return Settings(
        _env_file=None,
        admin_telegram_id="900001",
        premium_duration_days=30,
        premium_price="5000",
        telegram_premium_group_id="@premiumgroup",
    )


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


@pytest.fixture
def admin_context(admin_settings, session_factory):
    return BotContext(settings=admin_settings, session_factory=session_factory)


def _admin_update(admin_id: int = 900001, target_args: list[str] | None = None):
    user = User(id=admin_id, is_bot=False, first_name="Admin")
    chat = Chat(id=admin_id, type="private")
    message = MagicMock(spec=Message)
    message.chat = chat
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_message = message
    context = MagicMock()
    context.args = target_args if target_args is not None else ["123456789"]
    context.bot = AsyncMock()
    return update, context


class TestActivateCommand:
    async def test_denied_for_non_admin(self, admin_context):
        update, context = _admin_update(admin_id=111)
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}
        await activate_command(update, context)
        update.effective_message.reply_text.assert_awaited_once()
        assert "refusé" in update.effective_message.reply_text.await_args.args[0].lower()

    async def test_invalid_usage(self, admin_context):
        update, context = _admin_update(target_args=[])
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}
        await activate_command(update, context)
        assert "Usage" in update.effective_message.reply_text.await_args.args[0]

    async def test_activate_success(self, admin_context, monkeypatch):
        update, context = _admin_update(target_args=["888777666"])
        context.application = MagicMock()
        context.application.bot_data = {"ctx": admin_context}

        async def fake_invite(bot, settings, telegram_id):
            return GroupInviteResult(success=True, invite_link="https://t.me/+abc")

        monkeypatch.setattr(
            "app.bot.handlers.admin.invite_to_premium_group",
            fake_invite,
        )

        await activate_command(update, context)
        text = update.effective_message.reply_text.await_args.args[0]
        assert "Premium activé" in text
        assert "888777666" in text

        session = admin_context.session_factory()
        try:
            db_user = session.scalar(select(DbUser).where(DbUser.telegram_id == 888777666))
            assert db_user is not None
            subs = session.scalars(
                select(Subscription).where(Subscription.user_id == db_user.id)
            ).all()
            assert len(subs) == 1
            assert subs[0].statut == SubscriptionStatus.ACTIVE
        finally:
            session.close()
