"""Data Collector Sportmonks — orchestration principale."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.collectors.exceptions import (
    CollectorConfigError,
    NormalizationError,
    SportmonksAPIError,
)
from app.collectors.normalizers import normalize_fixture
from app.collectors.schemas import CollectionResult
from app.collectors.sportmonks_client import SportmonksClient
from app.config.settings import Settings, get_settings
from app.repositories.api_usage_repository import ApiUsageRepository
from app.repositories.football_repository import FootballRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class DataCollector:
    """
    Collecte les matchs Sportmonks, normalise et stocke en PostgreSQL.

    - Déduplication via external_match_id
    - Cache/fraîcheur via last_fetched_at + TTL PostgreSQL
    - Filtrage par ligues configurées (SPORTMONKS_LEAGUE_IDS)
    """

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        client: SportmonksClient | None = None,
    ):
        self.settings = settings or get_settings()
        self.session = session
        self.client = client or SportmonksClient(self.settings)
        self._owns_client = client is None
        self.football_repo = FootballRepository(session)
        self.api_usage_repo = ApiUsageRepository(session)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> DataCollector:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _validate_config(self) -> None:
        if not self.settings.has_database():
            raise CollectorConfigError("DATABASE_URL non configurée")
        if not self.settings.has_sportmonks():
            raise CollectorConfigError("SPORTMONKS_API_TOKEN non configuré")

    def _today_in_timezone(self) -> str:
        tz = ZoneInfo(self.settings.timezone)
        return datetime.now(tz).strftime("%Y-%m-%d")

    def _is_allowed_league(self, league_id: int | None, allowed: list[int]) -> bool:
        if not allowed:
            return True
        return league_id in allowed if league_id is not None else False

    def collect_for_date(self, target_date: str | None = None, *, force: bool = False) -> CollectionResult:
        """
        Collecte les matchs pour une date donnée (YYYY-MM-DD).

        Args:
            target_date: Date cible, défaut = aujourd'hui (timezone configurée)
            force: Ignorer le cache TTL et re-fetch
        """
        self._validate_config()
        date_str = target_date or self._today_in_timezone()
        result = CollectionResult(date=date_str)
        allowed_leagues = self.settings.get_sportmonks_league_ids()

        log_event(
            logger,
            "DATA_COLLECTION_STARTED",
            date=date_str,
            leagues=allowed_leagues or "all",
            force=force,
        )

        try:
            raw_fixtures = self.client.get_fixtures_by_date(
                date_str,
                league_ids=allowed_leagues or None,
            )
            result.api_requests = self.client.request_count
            result.fetched = len(raw_fixtures)
        except SportmonksAPIError as exc:
            result.errors = 1
            result.error_messages.append(str(exc))
            log_event(logger, "DATA_COLLECTION_FAILED", level="ERROR", error=str(exc))
            return result

        for raw in raw_fixtures:
            self._process_fixture(raw, allowed_leagues, force, result)

        self.api_usage_repo.increment(
            ApiUsageRepository.PROVIDER_SPORTMONKS,
            count=self.client.request_count,
        )

        log_event(
            logger,
            "DATA_COLLECTION_COMPLETED",
            date=date_str,
            fetched=result.fetched,
            stored=result.stored,
            skipped_fresh=result.skipped_fresh,
            skipped_league=result.skipped_league,
            skipped_placeholder=result.skipped_placeholder,
            errors=result.errors,
        )
        return result

    def _process_fixture(
        self,
        raw: dict,
        allowed_leagues: list[int],
        force: bool,
        result: CollectionResult,
    ) -> None:
        fixture_id = raw.get("id")
        league_id = raw.get("league_id")

        if not self._is_allowed_league(league_id, allowed_leagues):
            result.skipped_league += 1
            return

        if raw.get("placeholder"):
            result.skipped_placeholder += 1
            return

        if fixture_id and not force:
            existing = self.football_repo.get_match_by_external_id(int(fixture_id))
            if existing and self.football_repo.is_fresh(
                existing, self.settings.sportmonks_cache_ttl_minutes
            ):
                result.skipped_fresh += 1
                return

        try:
            normalized = normalize_fixture(raw, self.settings.timezone)
            self.football_repo.store_normalized_match(normalized)
            result.stored += 1
        except NormalizationError as exc:
            result.errors += 1
            result.error_messages.append(f"Fixture {fixture_id}: {exc}")
            log_event(
                logger,
                "FIXTURE_NORMALIZATION_FAILED",
                level="WARNING",
                fixture_id=fixture_id,
                error=str(exc),
            )
        except Exception as exc:
            result.errors += 1
            result.error_messages.append(f"Fixture {fixture_id}: {exc}")
            log_event(
                logger,
                "FIXTURE_STORE_FAILED",
                level="ERROR",
                fixture_id=fixture_id,
                error=str(exc),
            )

    def collect_between(self, start_date: str, end_date: str, *, force: bool = False) -> CollectionResult:
        """Collecte les matchs sur une plage de dates."""
        self._validate_config()
        result = CollectionResult(date=f"{start_date}..{end_date}")
        allowed_leagues = self.settings.get_sportmonks_league_ids()

        log_event(
            logger,
            "DATA_COLLECTION_STARTED",
            start=start_date,
            end=end_date,
            leagues=allowed_leagues or "all",
        )

        try:
            raw_fixtures = self.client.get_fixtures_between(
                start_date,
                end_date,
                league_ids=allowed_leagues or None,
            )
            result.api_requests = self.client.request_count
            result.fetched = len(raw_fixtures)
        except SportmonksAPIError as exc:
            result.errors = 1
            result.error_messages.append(str(exc))
            return result

        for raw in raw_fixtures:
            self._process_fixture(raw, allowed_leagues, force, result)

        self.api_usage_repo.increment(
            ApiUsageRepository.PROVIDER_SPORTMONKS,
            count=self.client.request_count,
        )

        log_event(
            logger,
            "DATA_COLLECTION_COMPLETED",
            start=start_date,
            end=end_date,
            stored=result.stored,
            errors=result.errors,
        )
        return result

    def refresh_fixture(self, external_match_id: int) -> bool:
        """Re-fetch un match spécifique par son ID Sportmonks."""
        self._validate_config()
        try:
            raw = self.client.get_fixture_by_id(external_match_id)
            normalized = normalize_fixture(raw, self.settings.timezone)
            self.football_repo.store_normalized_match(normalized)
            self.api_usage_repo.increment(ApiUsageRepository.PROVIDER_SPORTMONKS)
            return True
        except (SportmonksAPIError, NormalizationError) as exc:
            log_event(
                logger,
                "FIXTURE_REFRESH_FAILED",
                level="ERROR",
                fixture_id=external_match_id,
                error=str(exc),
            )
            return False
