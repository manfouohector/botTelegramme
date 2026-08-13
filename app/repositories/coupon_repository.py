"""Persistance des coupons."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.coupons.constants import COUPON_ENGINE_VERSION
from app.coupons.schemas import CouponCandidate, GeneratedCoupon
from app.database.enums import CouponStatus, CouponType
from app.models.coupon import Coupon, CouponPrediction, CouponVersion
from app.models.match import Match
from app.models.prediction import Prediction
from app.repositories.generation_repository import day_bounds
from app.repositories.prediction_repository import PredictionRepository


class CouponRepository:
    """Accès PostgreSQL pour coupons et versions."""

    def __init__(self, session: Session):
        self.session = session
        self.predictions = PredictionRepository(session)

    def save_coupon(
        self,
        generated: GeneratedCoupon,
        *,
        status: CouponStatus = CouponStatus.DRAFT,
        change_reason: str | None = None,
    ) -> Coupon:
        """Persiste un coupon généré avec ses prédictions."""
        if generated.skipped or not generated.candidates:
            raise ValueError("Impossible de persister un coupon vide")

        coupon = Coupon(
            type=generated.coupon_type,
            status=status,
            version=1,
            change_reason=change_reason,
        )
        self.session.add(coupon)
        self.session.flush()

        for position, candidate in enumerate(generated.candidates, start=1):
            market = self.predictions.get_or_create_market(
                candidate.market_code, name=candidate.market_code
            )
            model = self.predictions.get_or_create_model(
                name="coupon_pipeline",
                model_type="ensemble",
                version=COUPON_ENGINE_VERSION,
            )
            pred = Prediction(
                match_id=candidate.match_id,
                market_id=market.id,
                model_id=model.id,
                model_version=COUPON_ENGINE_VERSION,
                selection=candidate.selection,
                probability=Decimal(str(round(candidate.probability, 6))),
                odds=Decimal(str(round(candidate.decimal_odds, 4))),
                value_edge=Decimal(str(round(candidate.value_edge, 6)))
                if candidate.value_edge is not None
                else None,
                confidence=candidate.confidence,
                risk_decision=candidate.risk_decision.value,
            )
            self.session.add(pred)
            self.session.flush()

            self.session.add(
                CouponPrediction(
                    coupon_id=coupon.id,
                    prediction_id=pred.id,
                    position=position,
                )
            )

        self.session.add(
            CouponVersion(
                coupon_id=coupon.id,
                version=1,
                change_reason=change_reason or "Création initiale",
            )
        )
        self.session.flush()
        generated.coupon_id = coupon.id
        return coupon

    def publish_coupon(self, coupon_id: int) -> Coupon | None:
        coupon = self.session.get(Coupon, coupon_id)
        if coupon is None:
            return None
        coupon.status = CouponStatus.PUBLISHED
        coupon.published_at = datetime.now(timezone.utc)
        self.session.flush()
        return coupon

    def cancel_coupon(self, coupon_id: int, *, reason: str) -> Coupon | None:
        coupon = self.session.get(Coupon, coupon_id)
        if coupon is None:
            return None
        coupon.status = CouponStatus.CANCELLED
        coupon.change_reason = reason
        self.session.flush()
        return coupon

    def get_coupon_with_details(self, coupon_id: int) -> Coupon | None:
        return self.session.scalar(
            select(Coupon)
            .options(
                selectinload(Coupon.predictions)
                .selectinload(CouponPrediction.prediction)
                .selectinload(Prediction.market),
                selectinload(Coupon.predictions)
                .selectinload(CouponPrediction.prediction)
                .selectinload(Prediction.match)
                .selectinload(Match.home_team),
                selectinload(Coupon.predictions)
                .selectinload(CouponPrediction.prediction)
                .selectinload(Prediction.match)
                .selectinload(Match.away_team),
            )
            .where(Coupon.id == coupon_id)
        )

    def get_latest_published_by_type(
        self,
        coupon_type: CouponType,
        target_date: date,
        timezone_name: str,
    ) -> Coupon | None:
        start, end = day_bounds(target_date, timezone_name)
        return self.session.scalar(
            select(Coupon)
            .options(
                selectinload(Coupon.predictions)
                .selectinload(CouponPrediction.prediction)
                .selectinload(Prediction.market),
            )
            .where(
                Coupon.type == coupon_type,
                Coupon.status == CouponStatus.PUBLISHED,
                Coupon.published_at.is_not(None),
                Coupon.published_at >= start,
                Coupon.published_at <= end,
            )
            .order_by(Coupon.published_at.desc())
            .limit(1)
        )

    def create_new_version(
        self,
        coupon_id: int,
        *,
        change_reason: str,
    ) -> CouponVersion | None:
        coupon = self.session.get(Coupon, coupon_id)
        if coupon is None:
            return None
        coupon.version += 1
        version = CouponVersion(
            coupon_id=coupon_id,
            version=coupon.version,
            change_reason=change_reason,
        )
        self.session.add(version)
        self.session.flush()
        return version
