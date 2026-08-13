"""Tests unitaires — client Sportmonks."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from app.collectors.exceptions import (
    SportmonksAuthError,
    SportmonksEmptyResponseError,
    SportmonksRateLimitError,
    SportmonksTimeoutError,
)
from app.collectors.sportmonks_client import SportmonksClient
from app.config.settings import Settings

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


def _mock_response(status_code: int, json_data: dict | None = None, content: str = "") -> httpx.Response:
    request = httpx.Request("GET", "https://api.sportmonks.com/v3/football/fixtures/date/2026-08-13")
    if json_data is not None:
        return httpx.Response(status_code, json=json_data, request=request)
    return httpx.Response(status_code, content=content, request=request)


class TestSportmonksClient:
    @pytest.fixture
    def settings(self):
        return Settings(
            app_env="test",
            sportmonks_api_token="test-token",
            sportmonks_base_url="https://api.sportmonks.com/v3/football",
        )

    @pytest.fixture
    def mock_http(self):
        return MagicMock(spec=httpx.Client)

    def test_get_fixtures_by_date_success(self, settings, mock_http):
        payload = _load_fixture("sportmonks_fixtures_by_date.json")
        mock_http.request.return_value = _mock_response(200, payload)
        client = SportmonksClient(settings, mock_http)

        fixtures = client.get_fixtures_by_date("2026-08-13")
        assert len(fixtures) == 3
        assert fixtures[0]["id"] == 19146700
        assert client.request_count == 1

    def test_pagination_fetches_all_pages(self, settings, mock_http):
        page1 = {
            "data": [{"id": 1, "name": "Match 1"}],
            "pagination": {"has_more": True},
        }
        page2 = {
            "data": [{"id": 2, "name": "Match 2"}],
            "pagination": {"has_more": False},
        }
        mock_http.request.side_effect = [
            _mock_response(200, page1),
            _mock_response(200, page2),
        ]
        client = SportmonksClient(settings, mock_http)
        fixtures = client.get_fixtures_by_date("2026-08-13")
        assert len(fixtures) == 2
        assert client.request_count == 2

    def test_auth_error_401(self, settings, mock_http):
        mock_http.request.return_value = _mock_response(401, {"message": "Unauthorized"})
        client = SportmonksClient(settings, mock_http)
        with pytest.raises(SportmonksAuthError):
            client.get_fixtures_by_date("2026-08-13")

    def test_rate_limit_429(self, settings, mock_http):
        mock_http.request.return_value = _mock_response(429, {"message": "Too many requests"})
        client = SportmonksClient(settings, mock_http)
        with pytest.raises(SportmonksRateLimitError):
            client.get_fixtures_by_date("2026-08-13")

    def test_timeout(self, settings, mock_http):
        mock_http.request.side_effect = httpx.TimeoutException("timeout")
        client = SportmonksClient(settings, mock_http)
        with pytest.raises(SportmonksTimeoutError):
            client.get_fixtures_by_date("2026-08-13")

    def test_empty_response_no_data(self, settings, mock_http):
        mock_http.request.return_value = _mock_response(200, {"message": "empty"})
        client = SportmonksClient(settings, mock_http)
        with pytest.raises(SportmonksEmptyResponseError):
            client.get_fixtures_by_date("2026-08-13")

    def test_missing_token_raises(self, mock_http):
        settings = Settings(app_env="test", sportmonks_api_token="")
        client = SportmonksClient(settings, mock_http)
        with pytest.raises(SportmonksAuthError, match="SPORTMONKS_API_TOKEN"):
            client.get_fixtures_by_date("2026-08-13")

    def test_league_filter_param(self, settings, mock_http):
        mock_http.request.return_value = _mock_response(200, _load_fixture("sportmonks_fixtures_by_date.json"))
        client = SportmonksClient(settings, mock_http)
        client.get_fixtures_by_date("2026-08-13", league_ids=[501, 271])

        call_kwargs = mock_http.request.call_args
        params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
        assert params["filters"] == "fixtureLeagues:501,271"

    def test_get_fixture_by_id(self, settings, mock_http):
        payload = {"data": {"id": 123, "name": "Test Match"}}
        mock_http.request.return_value = _mock_response(200, payload)
        client = SportmonksClient(settings, mock_http)
        fixture = client.get_fixture_by_id(123)
        assert fixture["id"] == 123
