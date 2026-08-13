"""Tests unitaires — configuration."""

import pytest
from pydantic import ValidationError

from app.config.settings import Settings, get_settings


class TestSettingsDefaults:
    """Vérifie les valeurs par défaut."""

    def test_default_app_env(self):
        settings = Settings(_env_file=None)
        assert settings.app_env == "development"

    def test_default_timezone(self):
        settings = Settings(_env_file=None)
        assert settings.timezone == "Africa/Douala"

    def test_default_log_level(self):
        settings = Settings(_env_file=None)
        assert settings.log_level == "INFO"

    def test_default_llm_provider_none(self):
        settings = Settings(_env_file=None)
        assert settings.llm_provider == "none"
        assert settings.has_llm() is False


class TestSettingsValidation:
    """Vérifie la validation des champs."""

    def test_invalid_timezone_raises(self):
        with pytest.raises(ValidationError, match="Fuseau horaire invalide"):
            Settings(timezone="Invalid/Zone")

    def test_valid_timezone(self):
        settings = Settings(timezone="Europe/Paris")
        assert settings.timezone == "Europe/Paris"

    def test_invalid_time_format_raises(self):
        with pytest.raises(ValidationError, match="Heure hors limites"):
            Settings(daily_analysis_time="25:00")

    def test_invalid_time_format_non_numeric(self):
        with pytest.raises(ValidationError, match="Format horaire invalide"):
            Settings(daily_analysis_time="abc:de")

    def test_valid_time_format(self):
        settings = Settings(daily_analysis_time="08:30")
        assert settings.daily_analysis_time == "08:30"

    def test_invalid_app_env_raises(self):
        with pytest.raises(ValidationError):
            Settings(app_env="invalid")


class TestSettingsHelpers:
    """Vérifie les méthodes utilitaires."""

    def test_has_database_false_when_empty(self):
        settings = Settings(database_url="")
        assert settings.has_database() is False

    def test_has_database_true_when_set(self):
        settings = Settings(database_url="postgresql://user:pass@localhost/db")
        assert settings.has_database() is True

    def test_has_sportmonks(self):
        assert Settings(sportmonks_api_token="").has_sportmonks() is False
        assert Settings(sportmonks_api_token="token").has_sportmonks() is True

    def test_has_odds_api(self):
        assert Settings(odds_api_key="").has_odds_api() is False
        assert Settings(odds_api_key="key").has_odds_api() is True

    def test_has_telegram(self):
        assert Settings(telegram_bot_token="").has_telegram() is False
        assert Settings(telegram_bot_token="token").has_telegram() is True

    def test_has_llm_groq(self):
        settings = Settings(llm_provider="groq", groq_api_key="key")
        assert settings.has_llm() is True

    def test_has_llm_gemini(self):
        settings = Settings(llm_provider="gemini", gemini_api_key="key")
        assert settings.has_llm() is True

    def test_is_production(self):
        assert Settings(app_env="production").is_production is True
        assert Settings(app_env="development").is_production is False

    def test_strips_telegram_ids(self):
        settings = Settings(_env_file=None, admin_telegram_id="  123456789  ")
        assert settings.admin_telegram_id == "123456789"

    def test_get_sportmonks_league_ids(self):
        settings = Settings(_env_file=None, sportmonks_league_ids="501, 271, abc")
        assert settings.get_sportmonks_league_ids() == [501, 271]


class TestGetSettings:
    """Vérifie le singleton LRU."""

    def test_get_settings_returns_settings(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        get_settings.cache_clear()
        first = get_settings()
        second = get_settings()
        assert first is second

    def test_get_settings_reads_env(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "test")
        monkeypatch.setenv("APP_NAME", "Test Bot")
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.app_name == "Test Bot"
        get_settings.cache_clear()
