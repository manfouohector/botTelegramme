"""Schémas normalisés (DTO) pour le Data Collector."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal


@dataclass
class NormalizedCompetition:
    external_id: int
    name: str
    country: str | None = None
    code: str | None = None


@dataclass
class NormalizedSeason:
    external_id: int
    competition_external_id: int
    name: str
    is_current: bool = False


@dataclass
class NormalizedTeam:
    external_id: int
    name: str
    short_name: str | None = None


@dataclass
class NormalizedMatchStatistic:
    team_external_id: int
    stats: dict


@dataclass
class NormalizedMatch:
    external_match_id: int
    competition: NormalizedCompetition
    season: NormalizedSeason
    home_team: NormalizedTeam
    away_team: NormalizedTeam
    scheduled_at: datetime
    status: str
    home_score: int | None = None
    away_score: int | None = None
    data_status: str = "MISSING"
    statistics: list[NormalizedMatchStatistic] = field(default_factory=list)
    raw_state_id: int | None = None
    is_placeholder: bool = False
    has_statistics: bool = False
    has_participants: bool = False


@dataclass
class CollectionResult:
    """Résultat d'une exécution de collecte."""

    date: str
    fetched: int = 0
    stored: int = 0
    skipped_fresh: int = 0
    skipped_league: int = 0
    skipped_placeholder: int = 0
    errors: int = 0
    api_requests: int = 0
    error_messages: list[str] = field(default_factory=list)

    @property
    def total_processed(self) -> int:
        return self.stored + self.skipped_fresh + self.skipped_league + self.skipped_placeholder + self.errors
