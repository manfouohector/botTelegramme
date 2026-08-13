"""Tests unitaires — PremiumService."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.config.settings import Settings
from app.database.enums import PaymentStatus, SubscriptionStatus
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.services.premium_service import PremiumService
from sqlalchemy import select


@pytest.fixture
def premium_settings():
    return Settings(
        _env_file=None,
        premium_price="5000 FCFA",
        premium_amount=5000.0,
        premium_currency="XAF",
        premium_duration_days=30,
    )


class TestPremiumService:
    def test_activate_new_user(self, db_session, premium_settings):
        service = PremiumService(db_session, premium_settings)
        result = service.activate(999888777, admin_telegram_id=111)

        assert result.telegram_id == 999888777
        assert result.extended is False
        assert result.date_fin > result.date_debut

        sub = db_session.get(Subscription, result.subscription_id)
        assert sub.statut == SubscriptionStatus.ACTIVE

        payment = db_session.get(Payment, result.payment_id)
        assert payment.payment_status == PaymentStatus.SUCCESS
        assert payment.amount == Decimal("5000")

    def test_activate_extends_active_subscription(self, db_session, premium_settings):
        user = User(telegram_id=555444333)
        db_session.add(user)
        db_session.flush()

        now = datetime.now(timezone.utc)
        existing = Subscription(
            user_id=user.id,
            plan="premium",
            date_debut=now,
            date_fin=now + timedelta(days=10),
            statut=SubscriptionStatus.ACTIVE,
        )
        db_session.add(existing)
        db_session.flush()
        old_fin = existing.date_fin

        result = PremiumService(db_session, premium_settings).activate(555444333)
        assert result.extended is True
        assert result.date_fin > old_fin

    def test_is_premium(self, db_session, premium_settings):
        service = PremiumService(db_session, premium_settings)
        assert service.is_premium(123123123) is False
        service.activate(123123123)
        assert service.is_premium(123123123) is True

    def test_get_status_inactive(self, db_session, premium_settings):
        status = PremiumService(db_session, premium_settings).get_status(404404404)
        assert status.is_premium is False

    def test_creates_user_if_missing(self, db_session, premium_settings):
        PremiumService(db_session, premium_settings).activate(777666555)
        user = db_session.scalar(select(User).where(User.telegram_id == 777666555))
        assert user is not None
