"""Modèles contexte et risque."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.enums import InfoReliability


class ContextFactor(Base, TimestampMixin):
    __tablename__ = "context_factors"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    factor_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    source: Mapped[str | None] = mapped_column(String(100))
    reliability: Mapped[InfoReliability] = mapped_column(
        String(20), nullable=False, default=InfoReliability.OFFICIAL
    )

    match: Mapped["Match"] = relationship(back_populates="context_factors")


class RiskFactor(Base, TimestampMixin):
    __tablename__ = "risk_factors"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    factor: Mapped[str] = mapped_column(String(100), nullable=False)
    impact: Mapped[str | None] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="LOW")

    match: Mapped["Match"] = relationship(back_populates="risk_factors")
