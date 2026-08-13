"""Odds Collector — fetch The Odds API + persistance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from app.config.settings import Settings, get_settings
from app.models.match import Match
from app.repositories.api_usage_repository import ApiUsageRepository
from app.repositories.odds_repository import OddsRepository
from app.utils.logging import get_logger, log_event
from app.value.constants import ODDS_API_PROVIDER
from app.value.exceptions import OddsAPIError, OddsAuthError
from app.value.odds_api_client import OddsAPIClient
from app.value.odds_normalizer import normalize_odds_events
from app.value.schemas import NormalizedOdd

logger = get_logger(__name__)


class OddsCollector:
    """Collecte les cotes bookmakers via The Odds API."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        client: OddsAPIClient | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.client = client or OddsAPIClient(self.settings)
        self.odds_repo = OddsRepository(session)
        self.api_usage = ApiUsageRepository(session)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def collect_for_sport(self, sport_key: str) -> dict:
        """Collecte et lie les cotes d'un sport aux matchs PostgreSQL."""
        if not self.settings.has_odds_api():
            raise OddsAuthError("ODDS_API_KEY non configuré")

        events = self.client.get_odds_for_sport(sport_key)
        self.api_usage.increment(ODDS_API_PROVIDER, self.client.request_count)

        normalized = normalize_odds_events(events)
        linked = self._link_and_store(normalized)

        log_event(
            logger,
            "ODDS_COLLECTED",
            sport_key=sport_key,
            events=len(events),
            odds=len(normalized),
            linked=linked,
        )
        return {"sport_key": sport_key, "events": len(events), "odds": len(normalized), "linked": linked}

    def collect_for_match(self, match_id: int, sport_key: str) -> int:
        """Collecte les cotes pour un sport et ne persiste que celles du match."""
        if not self.settings.has_odds_api():
            raise OddsAuthError("ODDS_API_KEY non configuré")

        match = self.session.scalar(
            select(Match)
            .options(selectinload(Match.home_team), selectinload(Match.away_team))
            .where(Match.id == match_id)
        )
        if match is None:
            raise OddsAPIError(f"Match {match_id} introuvable")

        events = self.client.get_odds_for_sport(sport_key)
        self.api_usage.increment(ODDS_API_PROVIDER, self.client.request_count)

        normalized = normalize_odds_events(events)
        matched = [
            odd for odd in normalized
            if self._event_matches_match(odd, match)
        ]
        if matched:
            self.odds_repo.store_normalized_odds(match_id, matched)
        return len(matched)

    def _link_and_store(self, odds_list: list[NormalizedOdd]) -> int:
        linked = 0
        for event_id in {o.external_event_id for o in odds_list}:
            event_odds = [o for o in odds_list if o.external_event_id == event_id]
            if not event_odds:
                continue
            match = self._find_match_for_event(event_odds[0])
            if match is None:
                continue
            self.odds_repo.store_normalized_odds(match.id, event_odds)
            linked += 1
        return linked

    def _find_match_for_event(self, odd: NormalizedOdd) -> Match | None:
        tolerance = timedelta(hours=self.settings.odds_match_time_tolerance_hours)
        start = odd.commence_time - tolerance
        end = odd.commence_time + tolerance
        matches = self._fuzzy_find_match(odd, start, end)
        return matches[0] if matches else None

    def _fuzzy_find_match(self, odd: NormalizedOdd, start: datetime, end: datetime) -> list[Match]:
        candidates = list(
            self.session.scalars(
                select(Match)
                .options(selectinload(Match.home_team), selectinload(Match.away_team))
                .where(and_(Match.scheduled_at >= start, Match.scheduled_at <= end))
            ).all()
        )
        home_lower = odd.home_team.lower()
        away_lower = odd.away_team.lower()
        return [
            m for m in candidates
            if m.home_team and m.away_team
            and m.home_team.name.lower() == home_lower
            and m.away_team.name.lower() == away_lower
        ]

    @staticmethod
    def _event_matches_match(odd: NormalizedOdd, match: Match) -> bool:
        if not match.home_team or not match.away_team:
            return False
        names_ok = (
            match.home_team.name.lower() == odd.home_team.lower()
            and match.away_team.name.lower() == odd.away_team.lower()
        )
        if not names_ok:
            return False
        tolerance = timedelta(hours=3)
        delta = abs((match.scheduled_at - odd.commence_time).total_seconds())
        return delta <= tolerance.total_seconds()
