"""Modèle abonnement Premium."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.enums import SubscriptionStatus


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="premium")
    date_debut: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    date_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    statut: Mapped[SubscriptionStatus] = mapped_column(
        String(20), nullable=False, default=SubscriptionStatus.ACTIVE, index=True
    )

    user: Mapped["User"] = relationship(back_populates="subscriptions")
