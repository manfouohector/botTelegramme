"""Tests unitaires — client Odds API."""

from unittest.mock import MagicMock

import pytest

from app.config.settings import Settings
from app.value.exceptions import OddsAuthError, OddsRateLimitError
from app.value.odds_api_client import OddsAPIClient


def _mock_response(status: int, json_data=None, headers=None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data or []
    resp.headers = headers or {}
    return resp


class TestOddsAPIClient:
    @pytest.fixture
    def settings(self):
        return Settings(_env_file=None, odds_api_key="test-key")

    def test_get_odds_success(self, settings):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(
            200,
            [{"id": "1", "home_team": "A", "away_team": "B"}],
            headers={"x-requests-remaining": "100"},
        )
        client = OddsAPIClient(settings, http_client=mock_http)
        data = client.get_odds_for_sport("soccer_epl")
        assert len(data) == 1
        assert client.request_count == 1

    def test_missing_token_raises(self):
        client = OddsAPIClient(Settings(_env_file=None, odds_api_key=""))
        with pytest.raises(OddsAuthError):
            client.get_odds_for_sport("soccer_epl")

    def test_rate_limit_429(self, settings):
        mock_http = MagicMock()
        mock_http.request.return_value = _mock_response(429)
        client = OddsAPIClient(settings, http_client=mock_http)
        with pytest.raises(OddsRateLimitError):
            client.get_odds_for_sport("soccer_epl")
