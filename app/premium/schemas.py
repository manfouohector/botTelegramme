"""Schémas Premium / activation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ActivationResult:
    """Résultat d'une activation Premium admin."""

    user_id: int
    telegram_id: int
    subscription_id: int
    payment_id: int
    date_debut: datetime
    date_fin: datetime
    extended: bool
    username: str | None = None

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "telegram_id": self.telegram_id,
            "subscription_id": self.subscription_id,
            "payment_id": self.payment_id,
            "date_debut": self.date_debut.isoformat(),
            "date_fin": self.date_fin.isoformat(),
            "extended": self.extended,
            "username": self.username,
        }


@dataclass
class PremiumStatus:
    """Statut Premium d'un utilisateur."""

    is_premium: bool
    telegram_id: int
    date_fin: datetime | None = None
    plan: str | None = None

    def to_dict(self) -> dict:
        return {
            "is_premium": self.is_premium,
            "telegram_id": self.telegram_id,
            "date_fin": self.date_fin.isoformat() if self.date_fin else None,
            "plan": self.plan,
        }


@dataclass
class GroupInviteResult:
    """Résultat invitation groupe Premium."""

    success: bool
    invite_link: str | None = None
    reason: str | None = None
    user_notified: bool = False


@dataclass
class ExpiredSubscriptionResult:
    """Résultat expiration d'un abonnement."""

    subscription_id: int
    user_id: int
    telegram_id: int
    date_fin: datetime
    removed_from_group: bool = False
    user_notified: bool = False
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "subscription_id": self.subscription_id,
            "user_id": self.user_id,
            "telegram_id": self.telegram_id,
            "date_fin": self.date_fin.isoformat(),
            "removed_from_group": self.removed_from_group,
            "user_notified": self.user_notified,
            "error": self.error,
        }


@dataclass
class ExpirationBatchResult:
    """Résultat batch expiration abonnements."""

    processed: int = 0
    expired: int = 0
    removed_from_group: int = 0
    notified: int = 0
    skipped: int = 0
    errors: int = 0
    system_run_id: int | None = None
    items: list[ExpiredSubscriptionResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "processed": self.processed,
            "expired": self.expired,
            "removed_from_group": self.removed_from_group,
            "notified": self.notified,
            "skipped": self.skipped,
            "errors": self.errors,
            "system_run_id": self.system_run_id,
            "items": [i.to_dict() for i in self.items],
        }
