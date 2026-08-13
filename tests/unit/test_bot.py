"""Tests unitaires — infrastructure Bot Telegram."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import sessionmaker
from telegram import Chat, Message, Update, User

from app.bot.application import create_application
from app.bot.context import BotContext
from app.bot.exceptions import BotNotConfiguredError
from app.bot.handlers.fallback import non_command_message, unknown_command
from app.bot.handlers.health import ping_command
from app.bot.middleware import user_tracking_middleware
from app.bot.runner import run_bot
from app.config.settings import Settings
from app.repositories.user_repository import UserRepository


@pytest.fixture
def bot_settings():
    return Settings(
        _env_file=None,
        telegram_bot_token="123456789:AAFakeTokenForTests",
        app_name="Test Bot",
        database_url="sqlite:///:memory:",
    )


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


@pytest.fixture
def bot_context(bot_settings, session_factory):
    return BotContext(settings=bot_settings, session_factory=session_factory)


def _make_update(*, text: str = "/ping", user_id: int = 424242) -> Update:
    user = User(id=user_id, is_bot=False, first_name="Tester", username="tester")
    chat = Chat(id=user_id, type="private")
    message = MagicMock(spec=Message)
    message.chat = chat
    message.text = text
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_message = message
    return update


def _make_context(bot_context: BotContext) -> MagicMock:
    context = MagicMock()
    application = MagicMock()
    application.bot_data = {"ctx": bot_context}
    context.application = application
    context.error = RuntimeError("boom")
    return context


class TestBotApplication:
    def test_create_application_requires_token(self, session_factory, monkeypatch):
        monkeypatch.setattr(
            "app.bot.application.get_session_factory",
            lambda settings=None: session_factory,
        )
        with pytest.raises(BotNotConfiguredError):
            create_application(Settings(_env_file=None, telegram_bot_token=""))

    def test_create_application_success(self, bot_settings, session_factory, monkeypatch):
        monkeypatch.setattr(
            "app.bot.application.get_session_factory",
            lambda settings=None: session_factory,
        )
        app = create_application(bot_settings)
        assert app.bot_data["ctx"].settings.app_name == "Test Bot"
        assert app.handlers is not None

    def test_run_bot_raises_without_token(self):
        with pytest.raises(BotNotConfiguredError):
            run_bot(Settings(_env_file=None, telegram_bot_token=""))

    def test_lazy_import(self):
        from app.bot import BotContext, create_application

        assert BotContext is not None
        assert create_application is not None


class TestBotHandlers:
    async def test_ping_command(self, bot_context):
        update = _make_update(text="/ping")
        context = _make_context(bot_context)
        await ping_command(update, context)
        update.effective_message.reply_text.assert_awaited_once()
        assert "Test Bot" in update.effective_message.reply_text.await_args.args[0]

    async def test_unknown_command(self, bot_context):
        update = _make_update(text="/stats")
        context = _make_context(bot_context)
        await unknown_command(update, context)
        update.effective_message.reply_text.assert_awaited_once()
        text = update.effective_message.reply_text.await_args.args[0]
        assert "/start" in text
        assert "/stats" not in text or "non reconnue" in text

    async def test_non_command_message(self, bot_context):
        update = _make_update(text="hello")
        context = _make_context(bot_context)
        await non_command_message(update, context)
        update.effective_message.reply_text.assert_awaited_once()
        assert "/start" in update.effective_message.reply_text.await_args.args[0]


class TestBotMiddleware:
    async def test_user_tracking_creates_user(self, bot_context, db_engine):
        update = _make_update(user_id=777888999)
        context = _make_context(bot_context)
        await user_tracking_middleware(update, context)

        factory = bot_context.session_factory
        session = factory()
        try:
            user = UserRepository(session).get_by_telegram_id(777888999)
            assert user is not None
            assert user.username == "tester"
        finally:
            session.close()

    async def test_user_tracking_skips_without_user(self, bot_context):
        update = MagicMock(spec=Update)
        update.effective_user = None
        context = _make_context(bot_context)
        await user_tracking_middleware(update, context)


class TestBotErrorHandler:
    async def test_error_handler_replies(self, bot_context):
        from app.bot.handlers.errors import error_handler

        update = _make_update()
        context = _make_context(bot_context)
        await error_handler(update, context)
        update.effective_message.reply_text.assert_awaited_once()

    async def test_error_handler_without_message(self, bot_context):
        from app.bot.handlers.errors import error_handler

        update = MagicMock(spec=Update)
        update.effective_message = None
        context = _make_context(bot_context)
        await error_handler(update, context)
