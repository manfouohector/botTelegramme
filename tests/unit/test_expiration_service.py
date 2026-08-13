"""Tests unitaires — expiration abonnements."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.config.settings import Settings
from app.database.enums import SubscriptionStatus, SystemRunStatus
from app.models.subscription import Subscription
from app.models.system import SystemRun
from app.models.user import User
from app.repositories.subscription_repository import SubscriptionRepository
from app.services.expiration_service import SubscriptionExpirationService


@pytest.fixture
def expiration_settings():
    return Settings(
        _env_file=None,
        subscription_expiration_notify=True,
        telegram_premium_group_id="@premiumgroup",
        app_name="Test Bot",
    )


def _active_subscription(
    db_session,
    *,
    days_left: float = -1,
    telegram_id: int = 111222333,
) -> tuple[User, Subscription]:
    user = User(telegram_id=telegram_id, username=f"user{telegram_id}")
    db_session.add(user)
    db_session.flush()
    now = datetime.now(timezone.utc)
    sub = Subscription(
        user_id=user.id,
        plan="premium",
        date_debut=now - timedelta(days=30),
        date_fin=now + timedelta(days=days_left),
        statut=SubscriptionStatus.ACTIVE,
    )
    db_session.add(sub)
    db_session.flush()
    return user, sub


class TestSubscriptionRepositoryExpiration:
    def test_get_expired_active(self, db_session):
        user, expired = _active_subscription(db_session, days_left=-2)
        _active_subscription(db_session, days_left=10, telegram_id=444555666)

        repo = SubscriptionRepository(db_session)
        due = repo.get_expired_active()
        assert len(due) == 1
        assert due[0].id == expired.id

    def test_get_expired_active_empty(self, db_session):
        _active_subscription(db_session, days_left=5)
        assert SubscriptionRepository(db_session).get_expired_active() == []


class TestSubscriptionExpirationService:
    def test_expire_due_subscriptions(self, db_session, expiration_settings):
        user, sub = _active_subscription(db_session, days_left=-1)
        result = SubscriptionExpirationService(
            db_session, expiration_settings
        ).expire_due_subscriptions()

        assert result.processed == 1
        assert result.expired == 1
        assert result.errors == 0

        refreshed = db_session.get(Subscription, sub.id)
        assert refreshed.statut == SubscriptionStatus.EXPIRED
        assert SubscriptionRepository(db_session).get_active_for_user(user.id) is None

    def test_skips_future_subscriptions(self, db_session, expiration_settings):
        _active_subscription(db_session, days_left=15)
        result = SubscriptionExpirationService(
            db_session, expiration_settings
        ).expire_due_subscriptions()
        assert result.processed == 0
        assert result.expired == 0

    def test_records_system_run(self, db_session, expiration_settings):
        _active_subscription(db_session, days_left=-1)
        result = SubscriptionExpirationService(
            db_session, expiration_settings
        ).expire_due_subscriptions()

        assert result.system_run_id is not None
        run = db_session.get(SystemRun, result.system_run_id)
        assert run.run_type == "SUBSCRIPTION_EXPIRATION"
        assert run.status == SystemRunStatus.SUCCESS
        assert run.matches_processed == 1

    async def test_process_expirations_with_bot(self, db_session, expiration_settings, monkeypatch):
        user, sub = _active_subscription(db_session, days_left=-1)
        bot = AsyncMock()

        async def fake_remove(bot_arg, settings, telegram_id):
            from app.premium.schemas import GroupInviteResult

            assert telegram_id == user.telegram_id
            return GroupInviteResult(success=True)

        async def fake_notify(bot_arg, telegram_id, **kwargs):
            assert telegram_id == user.telegram_id
            return True

        monkeypatch.setattr(
            "app.services.expiration_service.remove_from_premium_group",
            fake_remove,
        )
        monkeypatch.setattr(
            "app.services.expiration_service.notify_subscription_expired",
            fake_notify,
        )

        result = await SubscriptionExpirationService(
            db_session, expiration_settings
        ).process_expirations(bot)

        assert result.expired == 1
        assert result.removed_from_group == 1
        assert result.notified == 1
        assert db_session.get(Subscription, sub.id).statut == SubscriptionStatus.EXPIRED

    async def test_process_without_bot_db_only(self, db_session, expiration_settings):
        _active_subscription(db_session, days_left=-1)
        result = await SubscriptionExpirationService(
            db_session, expiration_settings
        ).process_expirations(None, notify_users=False)

        assert result.expired == 1
        assert result.removed_from_group == 0
        assert result.notified == 0
