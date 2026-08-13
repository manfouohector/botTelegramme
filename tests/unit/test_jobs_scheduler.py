"""Tests unitaires — jobs planifiés."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config.settings import Settings
from app.database.enums import MatchStatus
from app.jobs.constants import JOB_FINAL_ANALYSIS, JOB_MAINTENANCE
from app.jobs.scheduler import create_scheduler, list_scheduled_jobs
from app.jobs.tasks import parse_hhmm, run_job_sync, run_maintenance
from app.models.football import Competition, Season, Team
from app.models.match import Match


@pytest.fixture
def job_settings():
    return Settings(
        _env_file=None,
        timezone="UTC",
        database_url="postgresql://test:test@localhost/test",
        scheduler_enable=True,
        daily_analysis_time="08:00",
        results_collection_time="23:00",
        settlement_time="23:30",
        subscription_expiration_time="00:00",
        final_analysis_check_interval_minutes=15,
        final_analysis_minutes_before=60,
    )


class TestJobHelpers:
    def test_parse_hhmm(self):
        assert parse_hhmm("08:30") == (8, 30)
        assert parse_hhmm("00:00") == (0, 0)


class TestScheduler:
    def test_create_scheduler_registers_jobs(self, job_settings):
        scheduler = create_scheduler(job_settings)
        job_ids = {job.id for job in scheduler.get_jobs()}
        assert "daily_analysis" in job_ids
        assert "final_analysis" in job_ids
        assert "results_collection" in job_ids
        assert "settlement" in job_ids
        assert "subscription_expiration" in job_ids
        assert "maintenance" in job_ids

    def test_list_scheduled_jobs(self, job_settings):
        jobs = list_scheduled_jobs(job_settings)
        assert len(jobs) == 6
        assert all("id" in job for job in jobs)


class TestMaintenanceJob:
    def test_maintenance_without_database(self):
        settings = Settings(_env_file=None, database_url="")
        result = run_maintenance(settings)
        assert result.success is False
        assert result.details["database_ok"] is False


class TestFinalAnalysisJob:
    async def test_skips_when_no_matches_in_window(self, job_settings):
        from app.jobs.tasks import run_final_analysis_async

        with patch("app.jobs.tasks.session_scope") as mock_scope:
            mock_session = MagicMock()
            mock_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
            mock_scope.return_value.__exit__ = MagicMock(return_value=False)
            with patch(
                "app.jobs.tasks.GenerationRepository.get_matches_starting_within_minutes",
                return_value=[],
            ):
                result = await run_final_analysis_async(job_settings)

        assert result.skipped is True
        assert result.reason == "no_matches_in_window"


class TestRunJobSync:
    def test_unknown_job_raises(self, job_settings):
        with pytest.raises(ValueError, match="Job inconnu"):
            run_job_sync("invalid_job", job_settings)

    def test_run_maintenance_via_sync(self, job_settings):
        with patch("app.jobs.tasks.check_database_connection", return_value=True):
            with patch("app.jobs.tasks.session_scope") as mock_scope:
                mock_session = MagicMock()
                mock_scope.return_value.__enter__ = MagicMock(return_value=mock_session)
                mock_scope.return_value.__exit__ = MagicMock(return_value=False)
                with patch("app.jobs.tasks.SystemRunRepository") as mock_repo_cls:
                    mock_repo = mock_repo_cls.return_value
                    mock_repo.start_run.return_value = MagicMock(id=1)
                    result = run_job_sync(JOB_MAINTENANCE, job_settings)
        assert result.job_name == JOB_MAINTENANCE
        assert result.success is True


class TestGenerationRepositoryWindow:
    def test_get_matches_starting_within_minutes(self, db_session):
        from app.repositories.generation_repository import GenerationRepository

        comp = Competition(external_id=501, name="L1", country="FR")
        db_session.add(comp)
        db_session.flush()
        season = Season(competition_id=comp.id, external_id=502, name="2026", is_current=True)
        db_session.add(season)
        db_session.flush()
        home = Team(external_id=503, name="A")
        away = Team(external_id=504, name="B")
        db_session.add_all([home, away])
        db_session.flush()

        now = datetime.now(timezone.utc)
        soon = Match(
            external_match_id=6001,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=now + timedelta(minutes=30),
            status=MatchStatus.SCHEDULED,
        )
        later = Match(
            external_match_id=6002,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=now + timedelta(hours=5),
            status=MatchStatus.SCHEDULED,
        )
        db_session.add_all([soon, later])
        db_session.flush()

        matches = GenerationRepository(db_session).get_matches_starting_within_minutes(
            60,
            "UTC",
        )
        assert len(matches) == 1
        assert matches[0].external_match_id == 6001
