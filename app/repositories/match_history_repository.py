"""Historique de matchs pour Feature Engineering — anti data leakage."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.enums import MatchStatus
from app.models.match import Match, MatchStatistic


from app.features.records import TeamMatchRecord


class MatchHistoryRepository:
    """
    Accès à l'historique de matchs AVANT une date de référence.

    Règle anti-leakage : scheduled_at < before_date ET status = FINISHED.
    """

    FINISHED = MatchStatus.FINISHED

    def __init__(self, session: Session):
        self.session = session

    def get_match_by_id(self, match_id: int) -> Match | None:
        return self.session.scalar(
            select(Match)
            .options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
                selectinload(Match.statistics),
            )
            .where(Match.id == match_id)
        )

    def get_team_finished_matches(
        self,
        team_id: int,
        before_date: datetime,
        *,
        season_id: int | None = None,
        limit: int = 10,
        venue: str | None = None,
    ) -> list[TeamMatchRecord]:
        """
        Matchs terminés d'une équipe avant une date.

        Args:
            venue: "home", "away" ou None pour tous
        """
        before = self._ensure_aware(before_date)
        conditions = [
            Match.status == self.FINISHED,
            Match.scheduled_at < before,
            Match.home_score.is_not(None),
            Match.away_score.is_not(None),
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
        ]
        if season_id is not None:
            conditions.append(Match.season_id == season_id)

        if venue == "home":
            conditions.append(Match.home_team_id == team_id)
        elif venue == "away":
            conditions.append(Match.away_team_id == team_id)

        stmt = (
            select(Match)
            .options(selectinload(Match.statistics))
            .where(and_(*conditions))
            .order_by(Match.scheduled_at.desc())
            .limit(limit)
        )
        matches = self.session.scalars(stmt).all()
        return [self._to_team_record(m, team_id) for m in matches]

    def get_h2h_matches(
        self,
        home_team_id: int,
        away_team_id: int,
        before_date: datetime,
        *,
        limit: int = 5,
    ) -> list[Match]:
        """Confrontations directes terminées avant la date."""
        before = self._ensure_aware(before_date)
        stmt = (
            select(Match)
            .where(
                Match.status == self.FINISHED,
                Match.scheduled_at < before,
                Match.home_score.is_not(None),
                Match.away_score.is_not(None),
                or_(
                    and_(Match.home_team_id == home_team_id, Match.away_team_id == away_team_id),
                    and_(Match.home_team_id == away_team_id, Match.away_team_id == home_team_id),
                ),
            )
            .order_by(Match.scheduled_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt).all())

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _to_team_record(self, match: Match, team_id: int) -> TeamMatchRecord:
        is_home = match.home_team_id == team_id
        goals_scored = match.home_score if is_home else match.away_score
        goals_conceded = match.away_score if is_home else match.home_score
        stats = {}
        for stat in match.statistics:
            if stat.team_id == team_id:
                stats = stat.stats or {}
                break

        return TeamMatchRecord(
            match_id=match.id,
            scheduled_at=self._ensure_aware(match.scheduled_at),
            team_id=team_id,
            opponent_id=match.away_team_id if is_home else match.home_team_id,
            is_home=is_home,
            goals_scored=int(goals_scored or 0),
            goals_conceded=int(goals_conceded or 0),
            stats=stats,
        )
