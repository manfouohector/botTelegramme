"""Tests unitaires — session et connexion DB."""

import pytest

from app.config.settings import Settings
from app.database.session import (
    check_database_connection,
    get_engine,
    reset_engine,
)


class TestDatabaseSession:
    def setup_method(self):
        reset_engine()

    def teardown_method(self):
        reset_engine()

    def test_get_engine_raises_without_database_url(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("DATABASE_URL", "")
        reset_engine()
        from app.config.settings import get_settings

        get_settings.cache_clear()
        with pytest.raises(RuntimeError, match="DATABASE_URL non configurée"):
            get_engine(Settings(database_url=""))

    def test_check_database_connection_false_without_url(self):
        assert check_database_connection(Settings(database_url="")) is False

    def test_reset_engine_clears_state(self, monkeypatch):
        """reset_engine ne doit pas lever d'exception même sans moteur initialisé."""
        reset_engine()
        reset_engine()
