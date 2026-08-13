"""Coupon Generator — SAFE / VALUE / HIGH_ODDS / FREE."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.coupons.constants import COUPON_ENGINE_VERSION
from app.coupons.schemas import CouponCandidate, CouponGenerationResult, GeneratedCoupon
from app.coupons.selectors import select_free, select_high_odds, select_safe, select_value
from app.database.enums import CouponStatus, CouponType
from app.repositories.coupon_repository import CouponRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class CouponGenerator:
    """
    Génère 0 à 4 coupons selon la qualité des sélections.

    Ne remplit jamais artificiellement un coupon.
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.coupon_repo = CouponRepository(session)

    def generate(
        self,
        candidates: list[CouponCandidate],
        *,
        include_free: bool = True,
        include_premium: bool = True,
        persist: bool = False,
        status: CouponStatus = CouponStatus.DRAFT,
    ) -> CouponGenerationResult:
        """Génère les coupons à partir des candidats publishable."""
        publishable = [c for c in candidates if c.publishable]

        safe = select_safe(publishable, self.settings) if include_premium else None
        value = select_value(publishable, self.settings) if include_premium else None
        high_odds = select_high_odds(publishable, self.settings) if include_premium else None

        premium_keys: set[tuple[int, str, str]] = set()
        for coupon in (safe, value, high_odds):
            if coupon and not coupon.skipped:
                premium_keys.update(c.candidate_key for c in coupon.candidates)

        free = (
            select_free(publishable, self.settings, exclude_keys=premium_keys)
            if include_free
            else None
        )

        result = CouponGenerationResult(
            free=free,
            safe=safe,
            value=value,
            high_odds=high_odds,
            metadata={
                "engine_version": COUPON_ENGINE_VERSION,
                "candidates_input": len(candidates),
                "candidates_publishable": len(publishable),
            },
        )

        if persist:
            for generated in result.all_coupons():
                self.coupon_repo.save_coupon(generated, status=status)

        log_event(
            logger,
            "COUPONS_GENERATED",
            created=result.coupons_created,
            publishable=len(publishable),
        )
        return result

    def generate_premium_only(
        self,
        candidates: list[CouponCandidate],
        *,
        persist: bool = False,
    ) -> CouponGenerationResult:
        """Phase 2 — SAFE, VALUE, HIGH_ODDS uniquement."""
        return self.generate(
            candidates,
            include_free=False,
            include_premium=True,
            persist=persist,
        )

    def generate_free_only(
        self,
        candidates: list[CouponCandidate],
        *,
        persist: bool = False,
    ) -> CouponGenerationResult:
        """Phase 1 matin — coupon gratuit vitrine."""
        return self.generate(
            candidates,
            include_free=True,
            include_premium=False,
            persist=persist,
        )
