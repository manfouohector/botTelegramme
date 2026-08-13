"""Tests unitaires — auth admin bot."""

from app.bot.auth import is_admin, parse_admin_id
from app.config.settings import Settings


class TestBotAuth:
    def test_is_admin_true(self):
        settings = Settings(_env_file=None, admin_telegram_id="123456789")
        assert is_admin(123456789, settings) is True

    def test_is_admin_false(self):
        settings = Settings(_env_file=None, admin_telegram_id="123456789")
        assert is_admin(999, settings) is False

    def test_is_admin_empty(self):
        settings = Settings(_env_file=None, admin_telegram_id="")
        assert is_admin(123, settings) is False

    def test_parse_admin_id(self):
        settings = Settings(_env_file=None, admin_telegram_id=" 42 ")
        assert parse_admin_id(settings) == 42
