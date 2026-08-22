"""Invitation au groupe Telegram Premium."""

from __future__ import annotations

from datetime import datetime

from telegram import Bot
from telegram.error import TelegramError

from app.config.settings import Settings
from app.premium.schemas import GroupInviteResult
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


async def invite_to_premium_group(
    bot: Bot,
    settings: Settings,
    telegram_id: int,
) -> GroupInviteResult:
    """
    Ajoute l'utilisateur au groupe Premium via lien d'invitation.

    Nécessite que le bot soit admin du groupe avec droits d'invitation.
    """
    group_id = settings.telegram_premium_group_id.strip()
    if not group_id:
        return GroupInviteResult(success=False, reason="premium_group_not_configured")

    try:
        await bot.unban_chat_member(
            chat_id=group_id,
            user_id=telegram_id,
            only_if_banned=True,
        )
    except TelegramError as exc:
        log_event(logger, "PREMIUM_UNBAN_FAILED", telegram_id=telegram_id, error=str(exc))

    try:
        invite = await bot.create_chat_invite_link(
            chat_id=group_id,
            member_limit=1,
            name=f"premium-{telegram_id}",
        )
        await bot.send_message(
            chat_id=telegram_id,
            text=(
                "👑 **Votre abonnement Premium est actif !**\n\n"
                f"Rejoignez le groupe exclusif :\n{invite.invite_link}\n\n"
                "Ce lien est personnel et à usage unique."
            ),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        log_event(logger, "PREMIUM_GROUP_INVITE_SENT", telegram_id=telegram_id)
        return GroupInviteResult(
            success=True,
            invite_link=invite.invite_link,
            user_notified=True,
        )
    except TelegramError as exc:
        log_event(logger, "PREMIUM_GROUP_INVITE_FAILED", telegram_id=telegram_id, error=str(exc))
        return GroupInviteResult(success=False, reason=str(exc))


async def remove_from_premium_group(
    bot: Bot,
    settings: Settings,
    telegram_id: int,
) -> GroupInviteResult:
    """
    Retire l'utilisateur du groupe Premium (ban puis unban pour réactivation future).
    """
    group_id = settings.telegram_premium_group_id.strip()
    if not group_id:
        return GroupInviteResult(success=False, reason="premium_group_not_configured")

    try:
        await bot.ban_chat_member(chat_id=group_id, user_id=telegram_id, revoke_messages=False)
        await bot.unban_chat_member(
            chat_id=group_id,
            user_id=telegram_id,
            only_if_banned=True,
        )
        log_event(logger, "PREMIUM_GROUP_REMOVED", telegram_id=telegram_id)
        return GroupInviteResult(success=True)
    except TelegramError as exc:
        log_event(logger, "PREMIUM_GROUP_REMOVE_FAILED", telegram_id=telegram_id, error=str(exc))
        return GroupInviteResult(success=False, reason=str(exc))


async def notify_subscription_expired(
    bot: Bot,
    telegram_id: int,
    *,
    expired_at: datetime,
    app_name: str,
) -> bool:
    """Envoie un message privé d'expiration."""
    from telegram.constants import ParseMode

    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=(
                f"⏳ **Abonnement Premium expiré — {app_name}**\n\n"
                f"Votre accès Premium a pris fin le **{expired_at.strftime('%d/%m/%Y')}**.\n"
                "Vous avez été retiré du groupe Premium.\n\n"
                "Pour renouveler : /premium"
            ),
            parse_mode=ParseMode.HTML,
        )
        log_event(logger, "PREMIUM_EXPIRATION_NOTIFIED", telegram_id=telegram_id)
        return True
    except TelegramError as exc:
        log_event(logger, "PREMIUM_EXPIRATION_NOTIFY_FAILED", telegram_id=telegram_id, error=str(exc))
        return False
