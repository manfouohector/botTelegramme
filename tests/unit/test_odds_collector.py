"""Tests unitaires — OddsCollector."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.config.settings import Settings
from app.repositories.api_usage_repository import ApiUsageRepository
from app.value.odds_collector import OddsCollector
from tests.fixtures.feature_helpers import seed_feature_test_data
from tests.fixtures.odds_helpers import ODDS_API_EVENT


class TestOddsCollector:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            odds_api_key="test-key",
            odds_match_time_tolerance_hours=24,
        )

    def test_collect_for_match(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        target = data["target_match"]
        target.scheduled_at = datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc)

        mock_client = MagicMock()
        mock_client.get_odds_for_sport.return_value = [ODDS_API_EVENT]
        mock_client.request_count = 1

        collector = OddsCollector(db_session, settings, client=mock_client)
        count = collector.collect_for_match(target.id, "soccer_france_ligue_one")

        assert count == 7  # 3 h2h + 2 totals + 2 btts
        usage = ApiUsageRepository(db_session).get_today_count("odds_api")
        assert usage == 1

    def test_collect_for_sport_links_match(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        data["target_match"].scheduled_at = datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc)

        mock_client = MagicMock()
        mock_client.get_odds_for_sport.return_value = [ODDS_API_EVENT]
        mock_client.request_count = 1

        collector = OddsCollector(db_session, settings, client=mock_client)
        result = collector.collect_for_sport("soccer_france_ligue_one")
        assert result["linked"] == 1
        assert result["odds"] == 7
