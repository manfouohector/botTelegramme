"""Tests d'intégration — Premium activation et expiration."""

from datetime import datetime, timedelta, timezone

from app.database.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.services.expiration_service import SubscriptionExpirationService
from app.services.premium_service import PremiumService


class TestPremiumLifecycle:
    def test_activate_then_expire(self, db_session, integration_settings):
        telegram_id = 987654321
        premium = PremiumService(db_session, integration_settings)

        activation = premium.activate(telegram_id)
        assert premium.is_premium(telegram_id) is True
        assert activation.subscription_id is not None

        sub = db_session.get(Subscription, activation.subscription_id)
        sub.date_fin = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.flush()

        expiration = SubscriptionExpirationService(
            db_session, integration_settings
        ).expire_due_subscriptions()
        assert expiration.expired == 1

        db_session.refresh(sub)
        assert sub.statut == SubscriptionStatus.EXPIRED
        assert premium.is_premium(telegram_id) is False

    def test_extend_then_still_active(self, db_session, integration_settings):
        telegram_id = 112233445
        premium = PremiumService(db_session, integration_settings)

        first = premium.activate(telegram_id)
        second = premium.activate(telegram_id)
        assert second.extended is True
        assert second.date_fin > first.date_fin
        assert premium.is_premium(telegram_id) is True

        result = SubscriptionExpirationService(
            db_session, integration_settings
        ).expire_due_subscriptions()
        assert result.expired == 0
