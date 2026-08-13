"""Modèles suivi système et usage API."""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.enums import SystemRunStatus


class ApiUsage(Base):
    __tablename__ = "api_usage"
    __table_args__ = (UniqueConstraint("provider", "date", name="uq_api_usage_provider_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SystemRun(Base):
    __tablename__ = "system_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[SystemRunStatus] = mapped_column(
        String(20), nullable=False, default=SystemRunStatus.RUNNING
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    matches_processed: Mapped[int] = mapped_column(Integer, default=0)
    predictions_created: Mapped[int] = mapped_column(Integer, default=0)
    coupons_created: Mapped[int] = mapped_column(Integer, default=0)
