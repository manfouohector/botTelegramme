"""Modèles coupons et versions."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.enums import CouponStatus, CouponType


class Coupon(Base, TimestampMixin):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[CouponType] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[CouponStatus] = mapped_column(
        String(20), nullable=False, default=CouponStatus.DRAFT, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    change_reason: Mapped[str | None] = mapped_column(Text)

    predictions: Mapped[list["CouponPrediction"]] = relationship(back_populates="coupon")
    versions: Mapped[list["CouponVersion"]] = relationship(back_populates="coupon")


class CouponPrediction(Base):
    __tablename__ = "coupon_predictions"
    __table_args__ = (UniqueConstraint("coupon_id", "position", name="uq_coupon_position"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(
        ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prediction_id: Mapped[int] = mapped_column(
        ForeignKey("predictions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    coupon: Mapped["Coupon"] = relationship(back_populates="predictions")
    prediction: Mapped["Prediction"] = relationship(back_populates="coupon_links")


class CouponVersion(Base):
    __tablename__ = "coupon_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(
        ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    change_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    coupon: Mapped["Coupon"] = relationship(back_populates="versions")
