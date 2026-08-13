"""Utilitaires bot — liens externes."""

from __future__ import annotations

from urllib.parse import quote


def build_telegram_channel_link(channel_id: str) -> str | None:
    """
    Construit un lien t.me depuis TELEGRAM_FREE_CHANNEL_ID.

    Formats acceptés : @username, username, -100xxxxxxxxxx, URL complète.
    """
    raw = channel_id.strip()
    if not raw:
        return None
    if raw.startswith("https://t.me/") or raw.startswith("http://t.me/"):
        return raw
    if raw.startswith("@"):
        return f"https://t.me/{raw[1:]}"
    if raw.startswith("-100") and raw[4:].isdigit():
        return f"https://t.me/c/{raw[4:]}"
    return f"https://t.me/{raw.lstrip('@')}"


def build_whatsapp_link(
    phone: str,
    *,
    telegram_id: int,
    username: str | None = None,
) -> str | None:
    """Lien wa.me avec message de souscription Premium pré-rempli."""
    digits = "".join(ch for ch in phone.strip() if ch.isdigit())
    if not digits:
        return None

    lines = [
        "Bonjour, je souhaite souscrire au Premium.",
        f"Mon ID Telegram est : {telegram_id}",
    ]
    if username:
        clean = username.lstrip("@")
        lines.append(f"Mon username est : @{clean}")

    text = quote("\n".join(lines), safe="")
    return f"https://wa.me/{digits}?text={text}"


def format_username_display(username: str | None) -> str:
    if not username:
        return "—"
    return f"@{username.lstrip('@')}"
