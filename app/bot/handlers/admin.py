"""Commandes admin — /activate, /generate, /status, /history."""

from __future__ import annotations

# pyrefly: ignore [missing-import]
from telegram import Update
# pyrefly: ignore [missing-import]
from telegram.ext import Application, CommandHandler, ContextTypes
# pyrefly: ignore [missing-import]
from telegram.constants import ParseMode

from app.bot.admin_messages import (
    format_daily_status,
    format_generation_error,
    format_generation_result,
    format_history_summary,
)
from app.bot.auth import is_admin
from app.bot.middleware import get_bot_context
from app.bot.services.group_service import invite_to_premium_group
from app.database.enums import SystemRunStatus
from app.services.generation_service import GenerationService
from app.services.history_service import HistoryService
from app.services.premium_service import PremiumService
from app.services.publication_service import PublicationService
from app.services.status_service import StatusService
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


def _format_activation_confirmation(result, *, invite_ok: bool, invite_reason: str | None) -> str:
    action = "prolongé" if result.extended else "activé"
    username = f"@{result.username.lstrip('@')}" if result.username else "—"
    lines = [
        "✅ **Premium activé**",
        "",
        f"• Utilisateur : `{result.telegram_id}` ({username})",
        f"• Abonnement : {action}",
        f"• Début : {result.date_debut.strftime('%d/%m/%Y %H:%M UTC')}",
        f"• Fin : {result.date_fin.strftime('%d/%m/%Y %H:%M UTC')}",
        f"• Paiement : enregistré (#{result.payment_id})",
    ]
    if invite_ok:
        lines.append("• Groupe Premium : invitation envoyée en privé")
    elif invite_reason == "premium_group_not_configured":
        lines.append("• Groupe Premium : non configuré (TELEGRAM_PREMIUM_GROUP_ID)")
    else:
        lines.append(f"• Groupe Premium : échec invitation ({invite_reason or 'erreur'})")
    return "\n".join(lines)


async def _deny_non_admin(message, user_id: int, command: str) -> None:
    await message.reply_text("⛔ Accès refusé. Cette commande est réservée à l'administrateur.")
    log_event(logger, f"BOT_{command.upper()}_DENIED", user_id=user_id)


async def activate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Active Premium pour un telegram_id — admin uniquement."""
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    bot_ctx = get_bot_context(context)
    settings = bot_ctx.settings

    if not is_admin(user.id, settings):
        await _deny_non_admin(message, user.id, "activate")
        return

    if not context.args or not context.args[0].isdigit():
        await message.reply_text(
            "**Usage :** `/activate <telegram_id>`\n\n"
            "Exemple : `/activate 123456789`",
        parse_mode=ParseMode.HTML,
        )
        return

    target_id = int(context.args[0])
    session = bot_ctx.session_factory()
    try:
        service = PremiumService(session, settings)
        result = service.activate(target_id, admin_telegram_id=user.id)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("BOT_ACTIVATE_FAILED | target_id=%s", target_id)
        await message.reply_text("❌ Erreur lors de l'activation. Consultez les logs.")
        return
    finally:
        session.close()

    invite = await invite_to_premium_group(context.bot, settings, target_id)

    await message.reply_text(
        _format_activation_confirmation(
            result,
            invite_ok=invite.success,
            invite_reason=invite.reason,
        ),
        parse_mode=ParseMode.HTML,
    )
    log_event(logger, "BOT_ACTIVATE_SUCCESS", target_id=target_id, admin_id=user.id)


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lance le pipeline complet — admin uniquement."""
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    bot_ctx = get_bot_context(context)
    settings = bot_ctx.settings

    if not is_admin(user.id, settings):
        await _deny_non_admin(message, user.id, "generate")
        return

    await message.reply_text("⏳ Génération en cours…")

    session = bot_ctx.session_factory()
    try:
        result = GenerationService(session, settings).run(
            skip_collector=not settings.has_sportmonks(),
            skip_odds_collector=not settings.has_odds_api(),
        )
        if (
            settings.publication_enable
            and settings.has_telegram()
            and result.coupon_result is not None
        ):
            pub = await PublicationService(session, settings).publish_from_generation(
                context.bot,
                result.coupon_result,
                target_date=result.target_date,
            )
            result.publication_result = pub
            result.published = pub.any_published or pub.any_confirmed
            result.publication_deferred = False
        elif not settings.publication_enable or not settings.has_telegram():
            result.publication_deferred = True
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("BOT_GENERATE_FAILED")
        await message.reply_text("❌ Erreur lors de la génération. Consultez les logs.")
        return
    finally:
        session.close()

    if result.status == SystemRunStatus.FAILED:
        text = format_generation_error(result)
    else:
        text = format_generation_result(result)

    await message.reply_text(text, parse_mode=ParseMode.HTML)
    log_event(
        logger,
        "BOT_GENERATE_SUCCESS",
        admin_id=user.id,
        coupons=result.coupons_created,
        run_id=result.system_run_id,
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Statut génération du jour — admin uniquement."""
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    bot_ctx = get_bot_context(context)
    settings = bot_ctx.settings

    if not is_admin(user.id, settings):
        await _deny_non_admin(message, user.id, "status")
        return

    session = bot_ctx.session_factory()
    try:
        status = StatusService(session, settings).get_daily_status()
    finally:
        session.close()

    await message.reply_text(format_daily_status(status), parse_mode=ParseMode.HTML)
    log_event(logger, "BOT_STATUS", admin_id=user.id)


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Historique coupons réglés — admin uniquement."""
    message = update.effective_message
    user = update.effective_user
    if message is None or user is None:
        return

    bot_ctx = get_bot_context(context)
    settings = bot_ctx.settings

    if not is_admin(user.id, settings):
        await _deny_non_admin(message, user.id, "history")
        return

    target_date = HistoryService.parse_date_arg(context.args[0] if context.args else None)
    if context.args and target_date is None:
        await message.reply_text(
            "**Usage :** `/history` ou `/history YYYY-MM-DD`",
        parse_mode=ParseMode.HTML,
        )
        return

    session = bot_ctx.session_factory()
    try:
        summary = HistoryService(session, settings).get_history(target_date)
    finally:
        session.close()

    await message.reply_text(format_history_summary(summary), parse_mode=ParseMode.HTML)
    log_event(logger, "BOT_HISTORY", admin_id=user.id, date=str(summary.target_date))


def register_admin_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("activate", activate_command))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("history", history_command))
