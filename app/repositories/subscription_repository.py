"""Persistance abonnements."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database.enums import SubscriptionStatus
from app.models.subscription import Subscription
from app.premium.constants import PREMIUM_PLAN


class SubscriptionRepository:
    """Accès PostgreSQL pour abonnements."""

    def __init__(self, session: Session):
        self.session = session

    def get_active_for_user(self, user_id: int) -> Subscription | None:
        now = datetime.now(timezone.utc)
        return self.session.scalar(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.statut == SubscriptionStatus.ACTIVE,
                Subscription.date_fin > now,
            )
            .order_by(Subscription.date_fin.desc())
        )

    def create_subscription(
        self,
        user_id: int,
        *,
        date_debut: datetime,
        date_fin: datetime,
        plan: str = PREMIUM_PLAN,
    ) -> Subscription:
        subscription = Subscription(
            user_id=user_id,
            plan=plan,
            date_debut=date_debut,
            date_fin=date_fin,
            statut=SubscriptionStatus.ACTIVE,
        )
        self.session.add(subscription)
        self.session.flush()
        return subscription

    def activate_or_extend(
        self,
        user_id: int,
        *,
        date_debut: datetime,
        date_fin: datetime,
    ) -> tuple[Subscription, bool]:
        """Active ou prolonge l'abonnement. Retourne (subscription, extended)."""
        existing = self.get_active_for_user(user_id)
        if existing is not None:
            existing.date_fin = date_fin
            existing.statut = SubscriptionStatus.ACTIVE
            self.session.flush()
            return existing, True

        stale = self.session.scalar(
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.statut == SubscriptionStatus.ACTIVE,
            )
            .order_by(Subscription.date_fin.desc())
        )
        if stale is not None:
            stale.date_debut = date_debut
            stale.date_fin = date_fin
            stale.statut = SubscriptionStatus.ACTIVE
            self.session.flush()
            return stale, False

        subscription = self.create_subscription(
            user_id,
            date_debut=date_debut,
            date_fin=date_fin,
        )
        return subscription, False

    def get_expired_active(self, *, as_of: datetime | None = None) -> list[Subscription]:
        """Abonnements ACTIVE dont date_fin est dépassée."""
        now = as_of or datetime.now(timezone.utc)
        return list(
            self.session.scalars(
                select(Subscription)
                .options(selectinload(Subscription.user))
                .where(
                    Subscription.statut == SubscriptionStatus.ACTIVE,
                    Subscription.date_fin <= now,
                )
                .order_by(Subscription.date_fin.asc())
            ).all()
        )

    def expire_subscription(self, subscription_id: int) -> Subscription | None:
        subscription = self.session.get(Subscription, subscription_id)
        if subscription is None:
            return None
        subscription.statut = SubscriptionStatus.EXPIRED
        self.session.flush()
        return subscription
