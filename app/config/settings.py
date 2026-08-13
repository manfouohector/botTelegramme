"""Chargement centralisé des variables d'environnement."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration applicative chargée depuis l'environnement."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production", "test"] = "development"
    app_name: str = "Football Prediction Bot"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    timezone: str = "Africa/Douala"

    # Database
    database_url: str = Field(default="", description="PostgreSQL connection URL")

    # Web service (Render / FastAPI)
    web_port: int = 8000

    # Sportmonks
    sportmonks_api_token: str = ""
    sportmonks_base_url: str = "https://api.sportmonks.com/v3/football"
    sportmonks_league_ids: str = Field(
        default="",
        description="IDs ligues Sportmonks séparés par des virgules (ex: 501,271)",
    )
    sportmonks_request_timeout: int = 30
    sportmonks_cache_ttl_minutes: int = 60
    sportmonks_per_page: int = 50

    # Odds API
    odds_api_key: str = ""
    odds_api_base_url: str = "https://api.the-odds-api.com/v4"
    odds_api_request_timeout: int = 30
    odds_api_regions: str = "eu"
    odds_api_markets: str = "h2h,totals,btts"
    odds_api_sport_keys: str = Field(
        default="",
        description="Clés sport Odds API séparées par virgules (ex: soccer_epl,soccer_france_ligue_one)",
    )
    odds_preferred_bookmaker: str = ""
    odds_match_time_tolerance_hours: int = 3
    value_use_normalized_implied: bool = True

    # Telegram
    telegram_bot_token: str = ""
    telegram_free_channel_id: str = ""
    telegram_premium_group_id: str = ""
    admin_telegram_id: str = ""
    telegram_bot_mode: Literal["polling", "webhook"] = "polling"
    telegram_webhook_url: str = ""
    telegram_webhook_port: int = 8443
    telegram_webhook_path: str = "telegram"
    telegram_request_timeout: int = 30
    telegram_drop_pending_updates: bool = True

    # WhatsApp / Premium V1
    whatsapp_phone: str = ""
    mobile_money_number: str = ""
    premium_price: str = ""
    premium_amount: float = 5000.0
    premium_currency: str = "XAF"
    premium_duration_days: int = 30

    # LLM (auxiliaire)
    llm_provider: Literal["groq", "gemini", "none"] = "none"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    # Scheduler
    daily_analysis_time: str = "08:00"
    final_analysis_minutes_before: int = 60
    final_analysis_check_interval_minutes: int = 15
    results_collection_time: str = "23:00"
    settlement_time: str = "23:30"
    subscription_expiration_time: str = "00:00"
    subscription_expiration_notify: bool = True
    scheduler_enable: bool = True

    # Publication Telegram
    publication_enable: bool = True
    publication_confirm_if_unchanged: bool = True

    # Prediction / Value / Risk
    value_edge_min_threshold: float = 0.05
    risk_reject_low_confidence: bool = True
    risk_reject_stale_data: bool = True
    risk_reject_incomplete_data: bool = True
    risk_stale_data_hours: int = 48
    risk_max_edge_threshold: float = 0.25
    risk_check_injuries: bool = True
    risk_check_lineups: bool = True

    # Coupon Generator
    coupon_safe_min_selections: int = 3
    coupon_safe_max_selections: int = 5
    coupon_safe_min_probability: float = 0.55
    coupon_safe_max_odds: float = 2.0
    coupon_value_min_selections: int = 2
    coupon_value_max_selections: int = 5
    coupon_allow_warning_in_value: bool = True
    coupon_high_odds_min_selections: int = 4
    coupon_high_odds_max_selections: int = 7
    coupon_high_odds_min_odds: float = 2.5
    coupon_high_odds_min_probability: float = 0.25
    coupon_high_odds_min_combined: float = 15.0
    coupon_free_min_selections: int = 3
    coupon_free_max_selections: int = 4
    coupon_free_min_probability: float = 0.50

    # Tracking
    tracking_settle_days_back: int = 14
    tracking_history_limit: int = 50

    # Backtesting / CLV
    backtest_min_matches: int = 10
    backtest_default_limit: int = 100
    clv_update_hours_before_kickoff: int = 1

    # Feature Engineering
    feature_form_window: int = 5
    feature_h2h_window: int = 5
    feature_min_matches: int = 3

    # Context Engine
    context_title_race_positions: int = 3
    context_relegation_positions: int = 3
    context_european_positions: int = 5
    context_high_stakes_points_gap: int = 6
    context_derby_pairs: str = Field(
        default="",
        description="Paires derby team_external_id:team_external_id séparées par des virgules",
    )

    # xG Engine
    xg_form_window: int = 5
    xg_min_matches: int = 3
    xg_min_training_samples: int = 20
    xg_enable_shot_proxy: bool = True

    # Prediction Engine
    prediction_max_goals: int = 6
    prediction_dixon_coles_rho: float = -0.13
    prediction_home_advantage: float = 1.10
    prediction_league_avg_home_goals: float = 1.45
    prediction_league_avg_away_goals: float = 1.15
    prediction_enable_dixon_coles: bool = True
    prediction_enable_ml: bool = True
    prediction_ml_min_samples: int = 30
    prediction_ensemble_poisson_weight: float = 0.65
    prediction_xg_blend_weight: float = 0.55
    prediction_min_matches: int = 3
    prediction_model_disagreement_threshold: float = 0.15
    prediction_markets: str = Field(
        default="1X2,BTTS,OU25",
        description="Marchés activés séparés par des virgules",
    )

    # Calibration
    calibration_enable: bool = True
    calibration_method: Literal["platt", "isotonic", "none"] = "isotonic"
    calibration_min_samples: int = 30
    calibration_bins: int = 10
    calibration_artifact_dir: str = "models/calibration"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        """Render/Heroku fournissent parfois postgres:// — SQLAlchemy attend postgresql://."""
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        """Vérifie que le fuseau horaire est reconnu par zoneinfo."""
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Fuseau horaire invalide : {value}") from exc
        return value

    @field_validator(
        "daily_analysis_time",
        "subscription_expiration_time",
        "results_collection_time",
        "settlement_time",
    )
    @classmethod
    def validate_time_format(cls, value: str) -> str:
        """Valide le format HH:MM."""
        parts = value.split(":")
        if len(parts) != 2:
            raise ValueError(f"Format horaire invalide : {value} (attendu HH:MM)")
        hour, minute = parts
        if not (hour.isdigit() and minute.isdigit()):
            raise ValueError(f"Format horaire invalide : {value}")
        h, m = int(hour), int(minute)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"Heure hors limites : {value}")
        return value

    @field_validator("admin_telegram_id", "telegram_free_channel_id", "telegram_premium_group_id")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        return value.strip()

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    def has_database(self) -> bool:
        return bool(self.database_url.strip())

    def has_sportmonks(self) -> bool:
        return bool(self.sportmonks_api_token.strip())

    def has_odds_api(self) -> bool:
        return bool(self.odds_api_key.strip())

    def has_telegram(self) -> bool:
        return bool(self.telegram_bot_token.strip())

    def has_whatsapp(self) -> bool:
        return bool(self.whatsapp_phone.strip())

    def has_free_channel(self) -> bool:
        return bool(self.telegram_free_channel_id.strip())

    def has_premium_group(self) -> bool:
        return bool(self.telegram_premium_group_id.strip())

    def has_llm(self) -> bool:
        if self.llm_provider == "groq":
            return bool(self.groq_api_key.strip())
        if self.llm_provider == "gemini":
            return bool(self.gemini_api_key.strip())
        return False

    def get_sportmonks_league_ids(self) -> list[int]:
        """Retourne la liste des IDs de ligues configurées."""
        if not self.sportmonks_league_ids.strip():
            return []
        ids: list[int] = []
        for part in self.sportmonks_league_ids.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        return ids

    def get_context_derby_pairs(self) -> list[tuple[int, int]]:
        """Retourne les paires de derby configurées (external team IDs)."""
        if not self.context_derby_pairs.strip():
            return []
        pairs: list[tuple[int, int]] = []
        for part in self.context_derby_pairs.split(","):
            part = part.strip()
            if ":" not in part:
                continue
            left, right = part.split(":", 1)
            if left.strip().isdigit() and right.strip().isdigit():
                a, b = int(left), int(right)
                pairs.append((min(a, b), max(a, b)))
        return pairs

    def get_prediction_markets(self) -> tuple[str, ...]:
        """Retourne les codes marchés activés."""
        if not self.prediction_markets.strip():
            from app.prediction.constants import DEFAULT_MARKETS
            return DEFAULT_MARKETS
        return tuple(
            part.strip().upper()
            for part in self.prediction_markets.split(",")
            if part.strip()
        )

    def get_odds_api_markets(self) -> str:
        return self.odds_api_markets.strip() or "h2h,totals,btts"

    def get_odds_api_sport_keys(self) -> list[str]:
        if not self.odds_api_sport_keys.strip():
            return []
        return [part.strip() for part in self.odds_api_sport_keys.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    """Retourne une instance singleton des settings (cache LRU)."""
    return Settings()
