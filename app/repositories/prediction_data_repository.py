"""Données d'entraînement pour le modèle ML."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.database.enums import MatchStatus
from app.models.match import Match
from app.prediction.constants import SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME


class PredictionDataRepository:
    """Charge les matchs terminés pour entraînement ML."""

    def __init__(self, session: Session):
        self.session = session

    def get_season_finished_matches(
        self,
        season_id: int,
        before_date: datetime,
        *,
        competition_id: int | None = None,
        exclude_match_id: int | None = None,
    ) -> list[Match]:
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
        if exclude_match_id is not None:
            conditions.append(Match.id != exclude_match_id)

        return list(
            self.session.scalars(
                select(Match)
                .where(and_(*conditions))
                .order_by(Match.scheduled_at.asc())
            ).all()
        )

    @staticmethod
    def match_outcome(match: Match) -> str:
        if match.home_score > match.away_score:
            return SELECTION_HOME
        if match.home_score == match.away_score:
            return SELECTION_DRAW
        return SELECTION_AWAY

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
