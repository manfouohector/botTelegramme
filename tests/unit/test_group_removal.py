"""Tests unitaires — retrait groupe Premium."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from telegram.error import TelegramError

from app.bot.services.group_service import notify_subscription_expired, remove_from_premium_group
from app.config.settings import Settings


@pytest.fixture
def group_settings():
    return Settings(
        _env_file=None,
        telegram_premium_group_id="@premiumgroup",
        app_name="Test Bot",
    )


class TestGroupRemoval:
    async def test_remove_success(self, group_settings):
        bot = AsyncMock()
        result = await remove_from_premium_group(bot, group_settings, 123456)
        assert result.success is True
        bot.ban_chat_member.assert_awaited_once()
        bot.unban_chat_member.assert_awaited_once()

    async def test_remove_no_group_configured(self):
        settings = Settings(_env_file=None, telegram_premium_group_id="")
        bot = AsyncMock()
        result = await remove_from_premium_group(bot, settings, 123)
        assert result.success is False
        bot.ban_chat_member.assert_not_called()

    async def test_remove_telegram_error(self, group_settings):
        bot = AsyncMock()
        bot.ban_chat_member.side_effect = TelegramError("forbidden")
        result = await remove_from_premium_group(bot, group_settings, 123)
        assert result.success is False

    async def test_notify_expiration(self, group_settings):
        bot = AsyncMock()
        ok = await notify_subscription_expired(
            bot,
            999,
            expired_at=datetime.now(timezone.utc),
            app_name="Test Bot",
        )
        assert ok is True
        bot.send_message.assert_awaited_once()
