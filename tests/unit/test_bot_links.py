"""Tests unitaires — liens bot."""

from urllib.parse import unquote

from app.bot.utils.links import (
    build_telegram_channel_link,
    build_whatsapp_link,
    format_username_display,
)


class TestTelegramChannelLink:
    def test_at_username(self):
        assert build_telegram_channel_link("@mychannel") == "https://t.me/mychannel"

    def test_plain_username(self):
        assert build_telegram_channel_link("mychannel") == "https://t.me/mychannel"

    def test_numeric_channel_id(self):
        assert build_telegram_channel_link("-1001234567890") == "https://t.me/c/1234567890"

    def test_full_url_passthrough(self):
        url = "https://t.me/joinchat/abc"
        assert build_telegram_channel_link(url) == url

    def test_empty_returns_none(self):
        assert build_telegram_channel_link("") is None
        assert build_telegram_channel_link("   ") is None


class TestWhatsAppLink:
    def test_builds_wa_me_link(self):
        link = build_whatsapp_link(
            "+237 6 99 00 00 00",
            telegram_id=123456789,
            username="johndoe",
        )
        assert link.startswith("https://wa.me/237699000000?text=")
        decoded = unquote(link.split("text=", 1)[1])
        assert "123456789" in decoded
        assert "@johndoe" in decoded

    def test_without_username(self):
        link = build_whatsapp_link("237600000000", telegram_id=42, username=None)
        decoded = unquote(link.split("text=", 1)[1])
        assert "Mon ID Telegram est : 42" in decoded
        assert "username" not in decoded

    def test_empty_phone_returns_none(self):
        assert build_whatsapp_link("", telegram_id=1) is None

    def test_format_username_display(self):
        assert format_username_display("john") == "@john"
        assert format_username_display("@john") == "@john"
        assert format_username_display(None) == "—"
