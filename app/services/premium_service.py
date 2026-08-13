"""Service Premium — activation et statut."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.database.enums import PaymentMethod
from app.premium.exceptions import UserNotFoundError
from app.premium.schemas import ActivationResult, PremiumStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.user_repository import UserRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class PremiumService:
    """Gestion abonnements Premium et paiements manuels."""

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.users = UserRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.payments = PaymentRepository(session)

    def get_status(self, telegram_id: int) -> PremiumStatus:
        user = self.users.get_by_telegram_id(telegram_id)
        if user is None:
            return PremiumStatus(is_premium=False, telegram_id=telegram_id)

        active = self.subscriptions.get_active_for_user(user.id)
        if active is None:
            return PremiumStatus(is_premium=False, telegram_id=telegram_id)

        return PremiumStatus(
            is_premium=True,
            telegram_id=telegram_id,
            date_fin=active.date_fin,
            plan=active.plan,
        )

    def is_premium(self, telegram_id: int) -> bool:
        return self.get_status(telegram_id).is_premium

    def activate(
        self,
        telegram_id: int,
        *,
        admin_telegram_id: int | None = None,
        reference: str | None = None,
    ) -> ActivationResult:
        """Active ou prolonge Premium. Crée l'utilisateur s'il n'existe pas."""
        user = self.users.get_by_telegram_id(telegram_id)
        if user is None:
            user, _ = self.users.get_or_create(telegram_id)

        now = datetime.now(timezone.utc)
        active = self.subscriptions.get_active_for_user(user.id)

        if active is not None:
            date_debut = active.date_debut
            active_fin = self._ensure_aware(active.date_fin)
            base = max(now, active_fin)
            date_fin = base + timedelta(days=self.settings.premium_duration_days)
            extended = True
        else:
            date_debut = now
            date_fin = now + timedelta(days=self.settings.premium_duration_days)
            extended = False

        subscription, _ = self.subscriptions.activate_or_extend(
            user.id,
            date_debut=date_debut,
            date_fin=date_fin,
        )

        amount = self._parse_premium_amount()
        payment = self.payments.record_success(
            user.id,
            amount=amount,
            currency=self.settings.premium_currency,
            method=PaymentMethod.MANUEL_WHATSAPP,
            reference=reference or (f"admin:{admin_telegram_id}" if admin_telegram_id else None),
        )

        log_event(
            logger,
            "PREMIUM_ACTIVATED",
            telegram_id=telegram_id,
            extended=extended,
            date_fin=date_fin.isoformat(),
            admin_id=admin_telegram_id,
        )

        return ActivationResult(
            user_id=user.id,
            telegram_id=telegram_id,
            subscription_id=subscription.id,
            payment_id=payment.id,
            date_debut=subscription.date_debut,
            date_fin=subscription.date_fin,
            extended=extended,
            username=user.username,
        )

    def _parse_premium_amount(self) -> Decimal:
        raw = self.settings.premium_price.strip()
        if not raw:
            return Decimal(str(self.settings.premium_amount))
        cleaned = re.sub(r"[^\d.,]", "", raw).replace(",", ".")
        try:
            return Decimal(cleaned) if cleaned else Decimal(str(self.settings.premium_amount))
        except InvalidOperation:
            return Decimal(str(self.settings.premium_amount))

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
