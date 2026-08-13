"""Service expiration automatique des abonnements Premium."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session
from telegram import Bot

from app.bot.services.group_service import notify_subscription_expired, remove_from_premium_group
from app.config.settings import Settings, get_settings
from app.database.enums import SystemRunStatus
from app.premium.expiration_constants import EXPIRATION_RUN_TYPE
from app.premium.schemas import ExpirationBatchResult, ExpiredSubscriptionResult
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.system_run_repository import SystemRunRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class SubscriptionExpirationService:
    """
    Expire les abonnements ACTIVE dont date_fin <= maintenant.

    Indépendant du système de paiement — basé uniquement sur date_fin.
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.subscriptions = SubscriptionRepository(session)
        self.system_runs = SystemRunRepository(session)

    def expire_due_subscriptions(
        self,
        *,
        as_of: datetime | None = None,
        record_run: bool = True,
    ) -> ExpirationBatchResult:
        """Expire en base uniquement (sans actions Telegram)."""
        due = self.subscriptions.get_expired_active(as_of=as_of)
        batch = ExpirationBatchResult(processed=len(due))

        run = self.system_runs.start_run(EXPIRATION_RUN_TYPE) if record_run else None
        if run is not None:
            batch.system_run_id = run.id

        for subscription in due:
            item = self._expire_subscription_record(subscription)
            batch.items.append(item)
            if item.error:
                batch.errors += 1
            else:
                batch.expired += 1

        if run is not None:
            status = SystemRunStatus.PARTIAL if batch.errors else SystemRunStatus.SUCCESS
            if batch.processed == 0:
                status = SystemRunStatus.SUCCESS
            self.system_runs.finish_run(
                run.id,
                status=status,
                processed=batch.expired,
                error_message=f"errors={batch.errors}" if batch.errors else None,
            )

        log_event(
            logger,
            "SUBSCRIPTIONS_EXPIRED",
            processed=batch.processed,
            expired=batch.expired,
            errors=batch.errors,
        )
        return batch

    async def process_expirations(
        self,
        bot: Bot | None = None,
        *,
        as_of: datetime | None = None,
        notify_users: bool | None = None,
        record_run: bool = True,
    ) -> ExpirationBatchResult:
        """Expire + retrait groupe + notification optionnelle."""
        notify = (
            notify_users
            if notify_users is not None
            else self.settings.subscription_expiration_notify
        )
        due = self.subscriptions.get_expired_active(as_of=as_of)
        batch = ExpirationBatchResult(processed=len(due))

        run = self.system_runs.start_run(EXPIRATION_RUN_TYPE) if record_run else None
        if run is not None:
            batch.system_run_id = run.id

        for subscription in due:
            item = self._expire_subscription_record(subscription)
            if item.error:
                batch.errors += 1
                batch.items.append(item)
                continue

            batch.expired += 1
            user = subscription.user
            if bot is not None and user is not None:
                remove = await remove_from_premium_group(
                    bot, self.settings, user.telegram_id
                )
                item.removed_from_group = remove.success

                if notify:
                    item.user_notified = await notify_subscription_expired(
                        bot,
                        user.telegram_id,
                        expired_at=subscription.date_fin,
                        app_name=self.settings.app_name,
                    )

                if item.removed_from_group:
                    batch.removed_from_group += 1
                if item.user_notified:
                    batch.notified += 1

            batch.items.append(item)

        if run is not None:
            status = SystemRunStatus.PARTIAL if batch.errors else SystemRunStatus.SUCCESS
            if batch.processed == 0:
                status = SystemRunStatus.SUCCESS
            self.system_runs.finish_run(
                run.id,
                status=status,
                processed=batch.expired,
                error_message=f"errors={batch.errors}" if batch.errors else None,
            )

        log_event(
            logger,
            "SUBSCRIPTION_EXPIRATION_BATCH",
            processed=batch.processed,
            expired=batch.expired,
            removed=batch.removed_from_group,
            notified=batch.notified,
        )
        return batch

    def _expire_subscription_record(self, subscription) -> ExpiredSubscriptionResult:
        user = subscription.user
        telegram_id = user.telegram_id if user else 0
        try:
            expired = self.subscriptions.expire_subscription(subscription.id)
            if expired is None:
                return ExpiredSubscriptionResult(
                    subscription_id=subscription.id,
                    user_id=subscription.user_id,
                    telegram_id=telegram_id,
                    date_fin=subscription.date_fin,
                    error="subscription_not_found",
                )
            return ExpiredSubscriptionResult(
                subscription_id=expired.id,
                user_id=expired.user_id,
                telegram_id=telegram_id,
                date_fin=expired.date_fin,
            )
        except Exception as exc:
            logger.exception("EXPIRE_SUBSCRIPTION_FAILED | id=%s", subscription.id)
            return ExpiredSubscriptionResult(
                subscription_id=subscription.id,
                user_id=subscription.user_id,
                telegram_id=telegram_id,
                date_fin=subscription.date_fin,
                error=str(exc),
            )
