"""Tests unitaires — service web FastAPI (Render)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.web_app import app
from app.config.settings import Settings, get_settings


@pytest.fixture
def web_client(monkeypatch):
    monkeypatch.setattr("app.api.web_app._ptb_application", None)
    get_settings.cache_clear()
    yield TestClient(app)
    get_settings.cache_clear()
    monkeypatch.setattr("app.api.web_app._ptb_application", None)


class TestWebApp:
    def test_health_endpoint(self, web_client, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()

        with patch("app.api.web_app.check_database_connection", return_value=True):
            response = web_client.get("/health")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database_ok"] is True

    def test_root_endpoint(self, web_client):
        response = web_client.get("/")
        assert response.status_code == 200
        assert response.json()["health"] == "/health"

    def test_webhook_not_initialized_returns_503(self, web_client, monkeypatch):
        get_settings.cache_clear()
        response = web_client.post("/telegram", json={"update_id": 1})
        assert response.status_code == 503

    def test_webhook_processes_update(self, web_client, monkeypatch):
        get_settings.cache_clear()
        fake_app = MagicMock()
        fake_app.bot = MagicMock()
        fake_app.process_update = AsyncMock()

        monkeypatch.setattr("app.api.web_app._ptb_application", fake_app)

        payload = {
            "update_id": 100,
            "message": {
                "message_id": 1,
                "date": 1_700_000_000,
                "chat": {"id": 1, "type": "private"},
                "text": "/start",
            },
        }
        with patch("app.api.web_app.Update.de_json", return_value=MagicMock()):
            response = web_client.post("/telegram", json=payload)
        assert response.status_code == 200
        fake_app.process_update.assert_awaited_once()

    def test_database_url_normalization(self):
        settings = Settings(_env_file=None, database_url="postgres://user:pass@host/db")
        assert settings.database_url.startswith("postgresql://")
