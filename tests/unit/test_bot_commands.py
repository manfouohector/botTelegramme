"""Tests unitaires — commandes bot /start /free /premium."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import sessionmaker
from telegram import CallbackQuery, Chat, Message, Update, User

from app.bot.handlers.callbacks import menu_callback
from app.bot.handlers.commands import free_command, premium_command, start_command
from app.bot.keyboards import CALLBACK_FREE, CALLBACK_PREMIUM
from app.config.settings import Settings
from tests.unit.test_bot import _make_context


@pytest.fixture
def session_factory(db_engine):
    return sessionmaker(bind=db_engine, autocommit=False, autoflush=False)


@pytest.fixture
def cmd_settings():
    return Settings(
        _env_file=None,
        app_name="Football Bot",
        telegram_free_channel_id="@freechannel",
        whatsapp_phone="237600000000",
        mobile_money_number="6XX XX XX XX",
        premium_price="5000 FCFA",
        premium_duration_days=30,
    )


@pytest.fixture
def cmd_context(cmd_settings, session_factory):
    from app.bot.context import BotContext

    return BotContext(settings=cmd_settings, session_factory=session_factory)


def _make_update_with_reply(*, text: str = "/start", user_id: int = 123456789) -> Update:
    user = User(id=user_id, is_bot=False, first_name="Jean", username="jean")
    chat = Chat(id=user_id, type="private")
    message = MagicMock(spec=Message)
    message.chat = chat
    message.chat_id = user_id
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.effective_message = message
    return update


class TestStartCommand:
    async def test_start_sends_welcome_and_keyboard(self, cmd_context):
        update = _make_update_with_reply(text="/start")
        context = _make_context(cmd_context)
        await start_command(update, context)
        update.effective_message.reply_text.assert_awaited_once()
        kwargs = update.effective_message.reply_text.await_args.kwargs
        assert "Football Bot" in update.effective_message.reply_text.await_args.args[0]
        assert kwargs["reply_markup"] is not None
        buttons = kwargs["reply_markup"].inline_keyboard
        assert buttons[0][0].text == "🟢 Canal Gratuit"
        assert buttons[0][0].url == "https://t.me/freechannel"


class TestFreeCommand:
    async def test_free_includes_channel_link(self, cmd_context):
        update = _make_update_with_reply(text="/free")
        context = _make_context(cmd_context)
        await free_command(update, context)
        text = update.effective_message.reply_text.await_args.args[0]
        assert "t.me/freechannel" in text

    async def test_free_without_channel_configured(self, cmd_context):
        cmd_context.settings.telegram_free_channel_id = ""
        update = _make_update_with_reply(text="/free")
        context = _make_context(cmd_context)
        await free_command(update, context)
        text = update.effective_message.reply_text.await_args.args[0]
        assert "pas encore configuré" in text.lower()


class TestPremiumCommand:
    async def test_premium_includes_price_and_whatsapp(self, cmd_context):
        update = _make_update_with_reply(text="/premium")
        context = _make_context(cmd_context)
        await premium_command(update, context)
        text = update.effective_message.reply_text.await_args.args[0]
        assert "5000 FCFA" in text
        assert "30 jours" in text
        assert "6XX XX XX XX" in text
        kwargs = update.effective_message.reply_text.await_args.kwargs
        markup = kwargs["reply_markup"]
        assert markup.inline_keyboard[0][0].url.startswith("https://wa.me/")
        assert "123456789" in markup.inline_keyboard[0][0].url

    async def test_premium_without_whatsapp(self, cmd_context):
        cmd_context.settings.whatsapp_phone = ""
        update = _make_update_with_reply(text="/premium")
        context = _make_context(cmd_context)
        await premium_command(update, context)
        text = update.effective_message.reply_text.await_args.args[0]
        assert "non configuré" in text.lower()
        kwargs = update.effective_message.reply_text.await_args.kwargs
        assert kwargs["reply_markup"] is None


class TestMenuCallbacks:
    async def test_callback_free(self, cmd_context):
        update = _make_update_with_reply()
        query = MagicMock(spec=CallbackQuery)
        query.data = CALLBACK_FREE
        query.message = update.effective_message
        query.answer = AsyncMock()
        update.callback_query = query

        context = _make_context(cmd_context)
        await menu_callback(update, context)
        query.answer.assert_awaited_once()
        update.effective_message.reply_text.assert_awaited()

    async def test_callback_premium(self, cmd_context):
        update = _make_update_with_reply()
        query = MagicMock(spec=CallbackQuery)
        query.data = CALLBACK_PREMIUM
        query.message = update.effective_message
        query.answer = AsyncMock()
        update.callback_query = query

        context = _make_context(cmd_context)
        await menu_callback(update, context)
        query.answer.assert_awaited_once()
        update.effective_message.reply_text.assert_awaited()
