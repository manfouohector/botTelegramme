"""Tests unitaires — normalizers Sportmonks."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.collectors.exceptions import NormalizationError
from app.collectors.normalizers import map_state_id, normalize_fixture, parse_starting_at
from app.database.enums import DataStatus, MatchStatus


class TestMapStateId:
    def test_not_started(self):
        assert map_state_id(1) == MatchStatus.SCHEDULED

    def test_full_time(self):
        assert map_state_id(5) == MatchStatus.FINISHED

    def test_postponed(self):
        assert map_state_id(10) == MatchStatus.POSTPONED

    def test_unknown_defaults_scheduled(self):
        assert map_state_id(999) == MatchStatus.SCHEDULED

    def test_none(self):
        assert map_state_id(None) == MatchStatus.SCHEDULED


class TestParseStartingAt:
    def test_valid_utc(self):
        dt = parse_starting_at("2026-08-13 14:00:00", "UTC")
        assert dt.tzinfo == ZoneInfo("UTC")
        assert dt.hour == 14

    def test_converts_to_timezone(self):
        dt = parse_starting_at("2026-08-13 14:00:00", "Europe/Paris")
        assert dt.tzinfo == ZoneInfo("Europe/Paris")

    def test_missing_raises(self):
        with pytest.raises(NormalizationError, match="starting_at manquant"):
            parse_starting_at(None)

    def test_invalid_format_raises(self):
        with pytest.raises(NormalizationError):
            parse_starting_at("invalid-date")


class TestNormalizeFixture:
    @pytest.fixture
    def sample_fixture(self):
        return {
            "id": 19146700,
            "league_id": 501,
            "season_id": 23690,
            "state_id": 1,
            "starting_at": "2026-08-13 14:00:00",
            "placeholder": False,
            "participants": [
                {"id": 180, "name": "St. Mirren", "short_code": "STM", "meta": {"location": "home"}},
                {"id": 65, "name": "Hibernian", "short_code": "HIB", "meta": {"location": "away"}},
            ],
            "league": {"id": 501, "name": "Premiership", "short_code": "SCO-P", "country": {"name": "Scotland"}},
            "season": {"id": 23690, "name": "2025/2026", "is_current": True},
            "statistics": [
                {"type_id": 42, "participant_id": 180, "data": {"value": 55}},
                {"type_id": 42, "participant_id": 65, "data": {"value": 45}},
            ],
        }

    def test_normalize_complete_fixture(self, sample_fixture):
        result = normalize_fixture(sample_fixture, "UTC")
        assert result.external_match_id == 19146700
        assert result.competition.name == "Premiership"
        assert result.home_team.name == "St. Mirren"
        assert result.away_team.name == "Hibernian"
        assert result.status == MatchStatus.SCHEDULED.value
        assert result.data_status == DataStatus.FRESH.value
        assert len(result.statistics) == 2

    def test_normalize_finished_with_scores(self):
        raw = {
            "id": 100,
            "league_id": 501,
            "season_id": 1,
            "state_id": 5,
            "starting_at": "2026-08-12 15:30:00",
            "participants": [
                {"id": 53, "name": "Celtic", "meta": {"location": "home"}},
                {"id": 62, "name": "Rangers", "meta": {"location": "away"}},
            ],
            "league": {"id": 501, "name": "Premiership"},
            "season": {"id": 1, "name": "2025/2026"},
            "scores": [
                {"description": "CURRENT", "score": {"goals": 2, "participant": "home"}},
                {"description": "CURRENT", "score": {"goals": 1, "participant": "away"}},
            ],
        }
        result = normalize_fixture(raw)
        assert result.home_score == 2
        assert result.away_score == 1
        assert result.status == MatchStatus.FINISHED.value

    def test_missing_participants_raises(self):
        with pytest.raises(NormalizationError, match="participants"):
            normalize_fixture({"id": 1, "league_id": 1, "season_id": 1, "starting_at": "2026-08-13 14:00:00"})

    def test_placeholder_incomplete_status(self):
        raw = {
            "id": 200,
            "league_id": 501,
            "season_id": 1,
            "starting_at": "2026-08-13 14:00:00",
            "placeholder": True,
            "participants": [
                {"id": 1, "name": "TBD 1", "meta": {"location": "home"}},
                {"id": 2, "name": "TBD 2", "meta": {"location": "away"}},
            ],
            "league": {"id": 501, "name": "Cup"},
            "season": {"id": 1, "name": "2025/2026"},
        }
        result = normalize_fixture(raw)
        assert result.data_status == DataStatus.INCOMPLETE.value
