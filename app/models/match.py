"""Modèle match et statistiques."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from app.database.types import JSONType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.enums import DataStatus, MatchStatus


class Match(Base, TimestampMixin):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_match_id: Mapped[int] = mapped_column(nullable=False, unique=True, index=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[MatchStatus] = mapped_column(
        String(20), nullable=False, default=MatchStatus.SCHEDULED, index=True
    )
    home_score: Mapped[int | None] = mapped_column(Integer)
    away_score: Mapped[int | None] = mapped_column(Integer)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_status: Mapped[DataStatus] = mapped_column(
        String(20), nullable=False, default=DataStatus.MISSING
    )

    competition: Mapped["Competition"] = relationship(back_populates="matches")
    season: Mapped["Season"] = relationship(back_populates="matches")
    home_team: Mapped["Team"] = relationship(back_populates="home_matches", foreign_keys=[home_team_id])
    away_team: Mapped["Team"] = relationship(back_populates="away_matches", foreign_keys=[away_team_id])
    statistics: Mapped[list["MatchStatistic"]] = relationship(back_populates="match")
    injuries: Mapped[list["Injury"]] = relationship(back_populates="match")
    lineups: Mapped[list["Lineup"]] = relationship(back_populates="match")
    odds: Mapped[list["Odd"]] = relationship(back_populates="match")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="match")
    context_factors: Mapped[list["ContextFactor"]] = relationship(back_populates="match")
    risk_factors: Mapped[list["RiskFactor"]] = relationship(back_populates="match")


class MatchStatistic(Base, TimestampMixin):
    __tablename__ = "match_statistics"
    __table_args__ = (UniqueConstraint("match_id", "team_id", name="uq_match_stat_team"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    stats: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)

    match: Mapped["Match"] = relationship(back_populates="statistics")
