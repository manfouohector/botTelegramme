"""Repository — persistance football (upsert PostgreSQL)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.schemas import NormalizedMatch, NormalizedMatchStatistic
from app.database.enums import DataStatus, MatchStatus
from app.models.football import Competition, Season, Team
from app.models.match import Match, MatchStatistic


class FootballRepository:
    """Accès données football avec déduplication par external_id."""

    def __init__(self, session: Session):
        self.session = session

    def get_match_by_external_id(self, external_match_id: int) -> Match | None:
        return self.session.scalar(
            select(Match).where(Match.external_match_id == external_match_id)
        )

    def is_fresh(self, match: Match, ttl_minutes: int) -> bool:
        """Vérifie si les données du match sont encore fraîches."""
        if match.last_fetched_at is None:
            return False
        if match.data_status in (DataStatus.MISSING, DataStatus.ERROR):
            return False
        threshold = datetime.now(timezone.utc) - timedelta(minutes=ttl_minutes)
        fetched = match.last_fetched_at
        if fetched.tzinfo is None:
            fetched = fetched.replace(tzinfo=timezone.utc)
        return fetched >= threshold

    def upsert_competition(self, external_id: int, name: str, country: str | None, code: str | None) -> Competition:
        comp = self.session.scalar(select(Competition).where(Competition.external_id == external_id))
        if comp is None:
            comp = Competition(external_id=external_id, name=name, country=country, code=code)
            self.session.add(comp)
        else:
            comp.name = name
            if country:
                comp.country = country
            if code:
                comp.code = code
        self.session.flush()
        return comp

    def upsert_season(
        self,
        external_id: int,
        competition_id: int,
        name: str,
        is_current: bool = False,
    ) -> Season:
        season = self.session.scalar(
            select(Season).where(
                Season.competition_id == competition_id,
                Season.external_id == external_id,
            )
        )
        if season is None:
            season = Season(
                external_id=external_id,
                competition_id=competition_id,
                name=name,
                is_current=is_current,
            )
            self.session.add(season)
        else:
            season.name = name
            season.is_current = is_current
        self.session.flush()
        return season

    def upsert_team(self, external_id: int, name: str, short_name: str | None) -> Team:
        team = self.session.scalar(select(Team).where(Team.external_id == external_id))
        if team is None:
            team = Team(external_id=external_id, name=name, short_name=short_name)
            self.session.add(team)
        else:
            team.name = name
            if short_name:
                team.short_name = short_name
        self.session.flush()
        return team

    def upsert_match_statistics(
        self,
        match_id: int,
        team_id: int,
        stats: dict,
    ) -> MatchStatistic:
        stat = self.session.scalar(
            select(MatchStatistic).where(
                MatchStatistic.match_id == match_id,
                MatchStatistic.team_id == team_id,
            )
        )
        if stat is None:
            stat = MatchStatistic(match_id=match_id, team_id=team_id, stats=stats)
            self.session.add(stat)
        else:
            stat.stats = stats
        self.session.flush()
        return stat

    def store_normalized_match(self, normalized: NormalizedMatch) -> Match:
        """Upsert complet : compétition, saison, équipes, match, stats."""
        now = datetime.now(timezone.utc)

        competition = self.upsert_competition(
            normalized.competition.external_id,
            normalized.competition.name,
            normalized.competition.country,
            normalized.competition.code,
        )
        season = self.upsert_season(
            normalized.season.external_id,
            competition.id,
            normalized.season.name,
            normalized.season.is_current,
        )
        home = self.upsert_team(
            normalized.home_team.external_id,
            normalized.home_team.name,
            normalized.home_team.short_name,
        )
        away = self.upsert_team(
            normalized.away_team.external_id,
            normalized.away_team.name,
            normalized.away_team.short_name,
        )

        match = self.get_match_by_external_id(normalized.external_match_id)
        if match is None:
            match = Match(
                external_match_id=normalized.external_match_id,
                competition_id=competition.id,
                season_id=season.id,
                home_team_id=home.id,
                away_team_id=away.id,
                scheduled_at=normalized.scheduled_at,
            )
            self.session.add(match)

        match.competition_id = competition.id
        match.season_id = season.id
        match.home_team_id = home.id
        match.away_team_id = away.id
        match.scheduled_at = normalized.scheduled_at
        match.status = MatchStatus(normalized.status)
        match.home_score = normalized.home_score
        match.away_score = normalized.away_score
        match.data_status = DataStatus(normalized.data_status)
        match.last_fetched_at = now

        self.session.flush()

        for stat in normalized.statistics:
            team = self.session.scalar(
                select(Team).where(Team.external_id == stat.team_external_id)
            )
            if team:
                self.upsert_match_statistics(match.id, team.id, stat.stats)

        return match
