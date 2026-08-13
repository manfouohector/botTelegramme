"""Tests unitaires — DataCollector."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from app.collectors.data_collector import DataCollector
from app.collectors.exceptions import CollectorConfigError, SportmonksAPIError
from app.collectors.sportmonks_client import SportmonksClient
from app.config.settings import Settings
from app.repositories.api_usage_repository import ApiUsageRepository

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class TestDataCollector:
    @pytest.fixture
    def settings(self):
        return Settings(
            app_env="test",
            timezone="UTC",
            database_url="sqlite:///:memory:",
            sportmonks_api_token="test-token",
            sportmonks_league_ids="501",
            sportmonks_cache_ttl_minutes=60,
        )

    @pytest.fixture
    def mock_client(self):
        client = MagicMock(spec=SportmonksClient)
        client.request_count = 1
        client.get_fixtures_by_date.return_value = _load_fixture("sportmonks_fixtures_by_date.json")["data"]
        return client

    def test_collect_for_date_stores_matches(self, db_session, settings, mock_client):
        collector = DataCollector(db_session, settings, mock_client)
        result = collector.collect_for_date("2026-08-13")

        assert result.fetched == 3
        assert result.stored == 2
        assert result.skipped_league == 1  # placeholder cup tie (league 999)
        assert result.errors == 0

        from sqlalchemy import select

        from app.models.match import Match

        matches = db_session.scalars(select(Match)).all()
        assert len(matches) == 2

    def test_collect_skips_fresh_cache(self, db_session, settings, mock_client):
        collector = DataCollector(db_session, settings, mock_client)
        first = collector.collect_for_date("2026-08-13")
        assert first.stored == 2

        second = collector.collect_for_date("2026-08-13")
        assert second.skipped_fresh == 2
        assert second.stored == 0

    def test_collect_force_bypasses_cache(self, db_session, settings, mock_client):
        collector = DataCollector(db_session, settings, mock_client)
        collector.collect_for_date("2026-08-13")

        result = collector.collect_for_date("2026-08-13", force=True)
        assert result.stored == 2
        assert result.skipped_fresh == 0

    def test_collect_tracks_api_usage(self, db_session, settings, mock_client):
        collector = DataCollector(db_session, settings, mock_client)
        collector.collect_for_date("2026-08-13")

        usage_repo = ApiUsageRepository(db_session)
        count = usage_repo.get_today_count(ApiUsageRepository.PROVIDER_SPORTMONKS)
        assert count == 1

    def test_collect_api_error(self, db_session, settings):
        mock_client = MagicMock(spec=SportmonksClient)
        mock_client.request_count = 0
        mock_client.get_fixtures_by_date.side_effect = SportmonksAPIError("API down")

        collector = DataCollector(db_session, settings, mock_client)
        result = collector.collect_for_date("2026-08-13")
        assert result.errors == 1
        assert result.stored == 0

    def test_collect_missing_config(self, db_session):
        settings = Settings(
            app_env="test",
            sportmonks_api_token="",
            database_url="sqlite:///:memory:",
        )
        collector = DataCollector(db_session, settings, MagicMock())
        with pytest.raises(CollectorConfigError, match="SPORTMONKS_API_TOKEN"):
            collector.collect_for_date("2026-08-13")

    def test_refresh_fixture(self, db_session, settings):
        mock_client = MagicMock(spec=SportmonksClient)
        mock_client.request_count = 1
        mock_client.get_fixture_by_id.return_value = _load_fixture("sportmonks_fixtures_by_date.json")["data"][0]

        collector = DataCollector(db_session, settings, mock_client)
        assert collector.refresh_fixture(19146700) is True

        from sqlalchemy import select

        from app.models.match import Match

        match = db_session.scalar(select(Match).where(Match.external_match_id == 19146700))
        assert match is not None

    def test_skips_placeholder_in_allowed_league(self, db_session, settings, mock_client):
        mock_client.get_fixtures_by_date.return_value = [
            {
                "id": 99999,
                "league_id": 501,
                "season_id": 23690,
                "state_id": 1,
                "starting_at": "2026-08-13 14:00:00",
                "placeholder": True,
                "participants": [
                    {"id": 1, "name": "TBD 1", "meta": {"location": "home"}},
                    {"id": 2, "name": "TBD 2", "meta": {"location": "away"}},
                ],
                "league": {"id": 501, "name": "Premiership"},
                "season": {"id": 23690, "name": "2025/2026"},
            }
        ]
        collector = DataCollector(db_session, settings, mock_client)
        result = collector.collect_for_date("2026-08-13")
        assert result.skipped_placeholder == 1
        assert result.stored == 0

    def test_league_filter_skips_other_leagues(self, db_session, settings, mock_client):
        settings.sportmonks_league_ids = "271"
        collector = DataCollector(db_session, settings, mock_client)
        result = collector.collect_for_date("2026-08-13")
        assert result.skipped_league == 3
        assert result.stored == 0
