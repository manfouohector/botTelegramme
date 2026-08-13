"""Accès données pour entraînement xG."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.database.enums import MatchStatus
from app.features.records import TeamMatchRecord
from app.models.match import Match


class XGDataRepository:
    """Charge les matchs terminés avec statistiques pour le xG."""

    def __init__(self, session: Session):
        self.session = session

    def get_season_training_records(
        self,
        season_id: int,
        before_date: datetime,
        *,
        competition_id: int | None = None,
    ) -> list[TeamMatchRecord]:
        """Tous les enregistrements équipe-match terminés avant une date."""
        before = self._ensure_aware(before_date)
        conditions = [
            Match.season_id == season_id,
            Match.status == MatchStatus.FINISHED,
            Match.scheduled_at < before,
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
        ]
        if competition_id is not None:
            conditions.append(Match.competition_id == competition_id)

        stmt = (
            select(Match)
            .options(selectinload(Match.statistics))
            .where(and_(*conditions))
            .order_by(Match.scheduled_at.asc())
        )
        matches = self.session.scalars(stmt).all()

        records: list[TeamMatchRecord] = []
        for match in matches:
            records.extend(self._match_to_records(match))
        return records

    @staticmethod
    def _match_to_records(match: Match) -> list[TeamMatchRecord]:
        records = []
        for team_id, is_home in [(match.home_team_id, True), (match.away_team_id, False)]:
            gs = match.home_score if is_home else match.away_score
            gc = match.away_score if is_home else match.home_score
            stats = {}
            for stat in match.statistics:
                if stat.team_id == team_id:
                    stats = stat.stats or {}
                    break
            records.append(
                TeamMatchRecord(
                    match_id=match.id,
                    scheduled_at=match.scheduled_at,
                    team_id=team_id,
                    opponent_id=match.away_team_id if is_home else match.home_team_id,
                    is_home=is_home,
                    goals_scored=int(gs or 0),
                    goals_conceded=int(gc or 0),
                    stats=stats,
                )
            )
        return records

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
