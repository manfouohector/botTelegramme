"""Calcul du classement à partir des matchs terminés — anti data leakage."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database.enums import MatchStatus
from app.models.match import Match


@dataclass
class _TeamAccumulator:
    team_id: int
    team_external_id: int
    team_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    points: int = 0
    goals_for: int = 0
    goals_against: int = 0


@dataclass
class StandingsSnapshot:
    """Classement calculé à un instant donné."""

    teams: list[_TeamAccumulator] = field(default_factory=list)
    total_teams: int = 0

    def sorted_by_rank(self) -> list[_TeamAccumulator]:
        return sorted(
            self.teams,
            key=lambda t: (t.points, t.goals_for - t.goals_against, t.goals_for),
            reverse=True,
        )


class StandingsCalculator:
    """
    Reconstruit le classement depuis les matchs FINISHED en base.

    Règle anti-leakage : scheduled_at < before_date, status = FINISHED.
    """

    def __init__(self, session: Session):
        self.session = session

    def compute(
        self,
        season_id: int,
        before_date: datetime,
        *,
        competition_id: int | None = None,
    ) -> StandingsSnapshot:
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
            .options(
                selectinload(Match.home_team),
                selectinload(Match.away_team),
            )
            .where(and_(*conditions))
        )
        matches = self.session.scalars(stmt).all()

        accumulators: dict[int, _TeamAccumulator] = {}

        for match in matches:
            self._ensure_team(accumulators, match.home_team_id, match.home_team)
            self._ensure_team(accumulators, match.away_team_id, match.away_team)

            home = accumulators[match.home_team_id]
            away = accumulators[match.away_team_id]
            hs, aws = match.home_score or 0, match.away_score or 0

            home.played += 1
            away.played += 1
            home.goals_for += hs
            home.goals_against += aws
            away.goals_for += aws
            away.goals_against += hs

            if hs > aws:
                home.wins += 1
                home.points += 3
                away.losses += 1
            elif hs < aws:
                away.wins += 1
                away.points += 3
                home.losses += 1
            else:
                home.draws += 1
                away.draws += 1
                home.points += 1
                away.points += 1

        return StandingsSnapshot(
            teams=list(accumulators.values()),
            total_teams=len(accumulators),
        )

    def count_remaining_matches(
        self,
        season_id: int,
        from_date: datetime,
        *,
        competition_id: int | None = None,
    ) -> int:
        """Compte les matchs encore SCHEDULED dans la saison à partir de from_date."""
        start = self._ensure_aware(from_date)
        conditions = [
            Match.season_id == season_id,
            Match.status == MatchStatus.SCHEDULED,
            Match.scheduled_at >= start,
        ]
        if competition_id is not None:
            conditions.append(Match.competition_id == competition_id)

        stmt = select(Match.id).where(and_(*conditions))
        return len(self.session.scalars(stmt).all())

    @staticmethod
    def _ensure_aware(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    @staticmethod
    def _ensure_team(accumulators: dict, team_id: int, team) -> None:
        if team_id not in accumulators and team is not None:
            accumulators[team_id] = _TeamAccumulator(
                team_id=team_id,
                team_external_id=team.external_id,
                team_name=team.name,
            )
