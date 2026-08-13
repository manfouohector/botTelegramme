"""Tests unitaires — GenerationService."""

from datetime import date, datetime, timezone

import pytest

from app.config.settings import Settings
from app.coupons.schemas import CouponGenerationResult, GeneratedCoupon
from app.database.enums import CouponType, SystemRunStatus
from app.generation.constants import GENERATION_RUN_TYPE
from app.generation.exceptions import GenerationStageError
from app.models.system import SystemRun
from app.repositories.odds_repository import OddsRepository
from app.services.generation_service import GenerationService
from app.value.odds_normalizer import normalize_odds_event
from tests.fixtures.feature_helpers import seed_feature_test_data
from tests.fixtures.odds_helpers import ODDS_API_EVENT


@pytest.fixture
def generation_settings():
    return Settings(
        _env_file=None,
        timezone="UTC",
        value_edge_min_threshold=0.05,
        coupon_safe_min_selections=1,
        coupon_value_min_selections=1,
        coupon_high_odds_min_selections=2,
        coupon_high_odds_min_combined=3.0,
        coupon_free_min_selections=1,
        coupon_safe_max_selections=4,
        coupon_value_max_selections=4,
        coupon_high_odds_max_selections=4,
        coupon_safe_min_probability=0.5,
        coupon_safe_max_odds=5.0,
        risk_check_injuries=False,
        risk_check_lineups=False,
        risk_reject_stale_data=False,
        calibration_enable=False,
        prediction_enable_ml=False,
    )


class TestGenerationService:
    def test_run_no_matches_today(self, db_session, generation_settings):
        result = GenerationService(db_session, generation_settings).run(
            target_date=date(2099, 1, 1),
            skip_collector=True,
            skip_odds_collector=True,
        )
        assert result.status == SystemRunStatus.SUCCESS
        assert result.matches_analyzed == 0
        assert result.coupons_created == 0
        assert result.system_run_id is not None

    def test_run_pipeline_with_seeded_match(self, db_session, generation_settings, monkeypatch):
        data = seed_feature_test_data(db_session)
        match = data["target_match"]
        match.scheduled_at = datetime(2026, 8, 20, 20, 0, tzinfo=timezone.utc)
        db_session.flush()

        normalized = normalize_odds_event(ODDS_API_EVENT)
        OddsRepository(db_session).store_normalized_odds(match.id, normalized)

        result = GenerationService(db_session, generation_settings).run(
            target_date=date(2026, 8, 20),
            skip_collector=True,
            skip_odds_collector=True,
            persist_coupons=True,
        )

        assert result.status in (SystemRunStatus.SUCCESS, SystemRunStatus.PARTIAL)
        assert result.matches_analyzed == 1
        assert result.predictions_created >= 1
        assert result.system_run_id is not None

        run = db_session.get(SystemRun, result.system_run_id)
        assert run.run_type == GENERATION_RUN_TYPE

    def test_collector_failure_marks_run_failed(self, db_session, generation_settings, monkeypatch):
        def boom(*args, **kwargs):
            raise GenerationStageError("DATA_COLLECTION", "timeout")

        monkeypatch.setattr(
            "app.services.generation_service.GenerationService._run_collector",
            boom,
        )

        result = GenerationService(db_session, generation_settings).run(
            target_date=date(2026, 8, 20),
            skip_collector=False,
            skip_odds_collector=True,
        )
        assert result.status == SystemRunStatus.FAILED
        assert result.failed_stage == "DATA_COLLECTION"
        assert "timeout" in (result.error_message or "")

    def test_skip_reasons_stored_in_run_metadata(self, db_session, generation_settings, monkeypatch):
        service = GenerationService(db_session, generation_settings)

        skipped = GeneratedCoupon(
            coupon_type=CouponType.HIGH_ODDS,
            candidates=[],
            total_odds=0.0,
            skipped=True,
            skip_reason="aucune sélection n'a passé le Risk Engine.",
        )
        fake_result = CouponGenerationResult(
            free=None,
            safe=None,
            value=None,
            high_odds=skipped,
        )

        class FakeMatch:
            id = 1

        monkeypatch.setattr(
            service.repo,
            "get_scheduled_matches_for_date",
            lambda *a, **k: [FakeMatch()],
        )
        monkeypatch.setattr(service, "_analyze_matches", lambda matches, batch: [])
        monkeypatch.setattr(service.coupon_generator, "generate", lambda *a, **k: fake_result)

        result = service.run(
            target_date=date(2026, 8, 20),
            skip_collector=True,
            skip_odds_collector=True,
        )
        assert "HIGH_ODDS" in result.skip_reasons

        run = db_session.get(SystemRun, result.system_run_id)
        assert run.error_message is not None
        assert run.error_message.startswith("GEN_META|")
