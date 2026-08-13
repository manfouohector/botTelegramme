"""Tests d'intégration — génération → publication → settlement → historique."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from app.backtesting.clv_service import ClvService
from app.database.enums import CouponStatus, CouponType, MatchStatus, SystemRunStatus
from app.models.coupon import Coupon
from app.repositories.coupon_repository import CouponRepository
from app.services.generation_service import GenerationService
from app.services.history_service import HistoryService
from app.services.publication_service import PublicationService
from app.services.status_service import StatusService
from app.tracking.tracking_engine import TrackingEngine


def _first_persisted_coupon(coupon_result):
    for generated in coupon_result.all_coupons():
        if generated.coupon_id is not None and not generated.skipped:
            return generated
    return None


class TestGenerationLifecycle:
    def test_generation_creates_coupons_and_system_run(
        self, db_session, integration_settings, seeded_match_day
    ):
        batch = GenerationService(db_session, integration_settings).run(
            target_date=seeded_match_day["target_date"],
            skip_collector=True,
            skip_odds_collector=True,
        )

        assert batch.status in (SystemRunStatus.SUCCESS, SystemRunStatus.PARTIAL)
        assert batch.matches_analyzed == 1
        assert batch.predictions_created >= 1
        assert batch.system_run_id is not None

        coupons = db_session.scalars(select(Coupon)).all()
        assert len(coupons) >= 1

    def test_status_reflects_generation_day(
        self, db_session, integration_settings, seeded_match_day
    ):
        GenerationService(db_session, integration_settings).run(
            target_date=seeded_match_day["target_date"],
            skip_collector=True,
            skip_odds_collector=True,
        )

        from app.models.system import SystemRun

        run = db_session.scalar(
            select(SystemRun).order_by(SystemRun.id.desc()).limit(1)
        )
        run.started_at = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
        db_session.flush()

        status = StatusService(db_session, integration_settings).get_daily_status(
            seeded_match_day["target_date"]
        )
        assert status.system_run_id is not None
        assert status.matches_analyzed >= 1
        assert len(status.coupons) >= 1

    async def test_publish_settle_and_history(
        self, db_session, integration_settings, seeded_match_day
    ):
        batch = GenerationService(db_session, integration_settings).run(
            target_date=seeded_match_day["target_date"],
            skip_collector=True,
            skip_odds_collector=True,
        )
        assert batch.coupon_result is not None

        repo = CouponRepository(db_session)
        generated = _first_persisted_coupon(batch.coupon_result)
        assert generated is not None and generated.coupon_id is not None

        phase = "free" if generated.coupon_type == CouponType.FREE else "premium"
        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=99))
        batch_pub = await PublicationService(db_session, integration_settings).publish_from_generation(
            bot,
            batch.coupon_result,
            phase=phase,
            target_date=seeded_match_day["target_date"],
            record_run=False,
        )
        assert batch_pub.published_count == 1

        coupon = repo.get_coupon_with_details(generated.coupon_id)
        assert coupon.status == CouponStatus.PUBLISHED

        clv_recorded = ClvService(db_session, integration_settings).record_publication_odds(
            generated.coupon_id
        )
        assert clv_recorded >= 0

        match = seeded_match_day["match"]
        match.status = MatchStatus.FINISHED
        match.home_score = 2
        match.away_score = 1
        db_session.flush()

        settlement = TrackingEngine(db_session, integration_settings).settle_pending()
        assert settlement.predictions_settled >= 1
        assert settlement.coupons_settled >= 1

        db_session.refresh(coupon)
        assert coupon.status == CouponStatus.SETTLED

        history = HistoryService(db_session, integration_settings).get_history(
            seeded_match_day["target_date"]
        )
        assert history.total_won + history.total_lost >= 1

    async def test_clv_analysis_after_settlement(
        self, db_session, integration_settings, seeded_match_day
    ):
        batch = GenerationService(db_session, integration_settings).run(
            target_date=seeded_match_day["target_date"],
            skip_collector=True,
            skip_odds_collector=True,
        )
        generated = _first_persisted_coupon(batch.coupon_result)
        assert generated is not None

        phase = "free" if generated.coupon_type == CouponType.FREE else "premium"
        bot = AsyncMock()
        bot.send_message = AsyncMock(return_value=MagicMock(message_id=99))
        await PublicationService(db_session, integration_settings).publish_from_generation(
            bot,
            batch.coupon_result,
            phase=phase,
            target_date=seeded_match_day["target_date"],
            record_run=False,
        )

        match = seeded_match_day["match"]
        match.status = MatchStatus.FINISHED
        match.home_score = 2
        match.away_score = 1
        db_session.flush()

        TrackingEngine(db_session, integration_settings).settle_pending()

        report = ClvService(db_session, integration_settings).analyze_published_clv()
        assert report.sample_size >= 1
