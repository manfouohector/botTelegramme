"""Tests unitaires — runner webhook."""

import pytest

from app.bot.exceptions import BotNotConfiguredError
from app.bot.runner import run_bot
from app.config.settings import Settings


class TestBotRunner:
    def test_webhook_requires_url(self, monkeypatch):
        settings = Settings(
            _env_file=None,
            telegram_bot_token="123:ABC",
            telegram_bot_mode="webhook",
            telegram_webhook_url="",
            database_url="sqlite:///:memory:",
        )
        monkeypatch.setattr("app.bot.runner.setup_logging", lambda s: None)
        monkeypatch.setattr(
            "app.bot.runner.create_application",
            lambda s=None: (_ for _ in ()).throw(AssertionError("should not build app")),
        )

        with pytest.raises(BotNotConfiguredError, match="WEBHOOK_URL"):
            run_bot(settings)

    def test_run_polling_delegates(self, monkeypatch):
        settings = Settings(
            _env_file=None,
            telegram_bot_token="123:ABC",
            telegram_bot_mode="polling",
            database_url="sqlite:///:memory:",
        )
        called = {}

        class FakeApp:
            def run_polling(self, **kwargs):
                called["polling"] = kwargs

        monkeypatch.setattr("app.bot.runner.setup_logging", lambda s: None)
        monkeypatch.setattr("app.bot.runner.create_application", lambda s=None: FakeApp())

        run_bot(settings)
        assert "polling" in called
        assert called["polling"]["drop_pending_updates"] is True
