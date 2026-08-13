"""Modèles marchés et cotes."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Market(Base, TimestampMixin):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    active: Mapped[bool] = mapped_column(default=False)

    odds: Mapped[list["Odd"]] = relationship(back_populates="market")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="market")


class Odd(Base, TimestampMixin):
    __tablename__ = "odds"
    __table_args__ = (
        UniqueConstraint(
            "match_id", "market_id", "bookmaker", "selection", "fetched_at",
            name="uq_odd_match_market_book_selection_fetched",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    market_id: Mapped[int] = mapped_column(
        ForeignKey("markets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    bookmaker: Mapped[str] = mapped_column(String(100), nullable=False)
    selection: Mapped[str] = mapped_column(String(100), nullable=False)
    odds: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    implied_probability: Mapped[Decimal | None] = mapped_column(Numeric(8, 6))
    opening_odds: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    closing_odds: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    match: Mapped["Match"] = relationship(back_populates="odds")
    market: Mapped["Market"] = relationship(back_populates="odds")
