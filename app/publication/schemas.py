"""Schémas publication Telegram."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.database.enums import CouponType


@dataclass
class PublishedCouponResult:
    """Résultat publication d'un coupon."""

    coupon_type: CouponType
    coupon_id: int | None = None
    success: bool = False
    confirmed_only: bool = False
    skipped: bool = False
    reason: str | None = None
    message_id: int | None = None
    chat_id: str | None = None

    def to_dict(self) -> dict:
        return {
            "coupon_type": self.coupon_type.value,
            "coupon_id": self.coupon_id,
            "success": self.success,
            "confirmed_only": self.confirmed_only,
            "skipped": self.skipped,
            "reason": self.reason,
            "message_id": self.message_id,
            "chat_id": self.chat_id,
        }


@dataclass
class PublicationBatchResult:
    """Résultat batch publication."""

    items: list[PublishedCouponResult] = field(default_factory=list)
    system_run_id: int | None = None
    errors: int = 0

    @property
    def any_published(self) -> bool:
        return any(i.success and not i.confirmed_only for i in self.items)

    @property
    def any_confirmed(self) -> bool:
        return any(i.confirmed_only for i in self.items)

    @property
    def published_count(self) -> int:
        return sum(1 for i in self.items if i.success and not i.confirmed_only)

    def to_dict(self) -> dict:
        return {
            "items": [i.to_dict() for i in self.items],
            "system_run_id": self.system_run_id,
            "errors": self.errors,
            "any_published": self.any_published,
            "published_count": self.published_count,
        }
