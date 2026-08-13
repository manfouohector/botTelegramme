"""Modèles joueur, blessures et compositions."""

from sqlalchemy import ForeignKey, String, UniqueConstraint
from app.database.types import JSONType
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.database.enums import InfoReliability


class Player(Base, TimestampMixin):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[int] = mapped_column(nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    position: Mapped[str | None] = mapped_column(String(50))

    injuries: Mapped[list["Injury"]] = relationship(back_populates="player")


class Injury(Base, TimestampMixin):
    __tablename__ = "injuries"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id", ondelete="SET NULL"), index=True
    )
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    injury_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str | None] = mapped_column(String(50))
    reliability: Mapped[InfoReliability] = mapped_column(
        String(20), nullable=False, default=InfoReliability.OFFICIAL
    )

    match: Mapped["Match"] = relationship(back_populates="injuries")
    player: Mapped["Player | None"] = relationship(back_populates="injuries")


class Lineup(Base, TimestampMixin):
    __tablename__ = "lineups"
    __table_args__ = (UniqueConstraint("match_id", "team_id", name="uq_lineup_match_team"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    formation: Mapped[str | None] = mapped_column(String(20))
    players: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    reliability: Mapped[InfoReliability] = mapped_column(
        String(20), nullable=False, default=InfoReliability.PROBABLE
    )

    match: Mapped["Match"] = relationship(back_populates="lineups")
