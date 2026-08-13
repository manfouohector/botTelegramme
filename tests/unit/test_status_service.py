"""Tests unitaires — StatusService."""

from datetime import datetime, timezone

import pytest

from app.config.settings import Settings
from app.database.enums import CouponType, SystemRunStatus
from app.generation.constants import GENERATION_RUN_TYPE
from app.models.system import SystemRun
from app.services.status_service import StatusService
from tests.fixtures.generation_helpers import seed_status_day


@pytest.fixture
def status_settings():
    return Settings(_env_file=None, timezone="UTC")


class TestStatusService:
    def test_daily_status_with_run_and_coupons(self, db_session, status_settings):
        day = datetime(2026, 8, 12, 8, 0, tzinfo=timezone.utc)
        seeded = seed_status_day(db_session, day=day, timezone_name="UTC")

        status = StatusService(db_session, status_settings).get_daily_status(seeded["day"])

        assert status.matches_analyzed == 18
        assert status.predictions_created == 42
        assert status.run_status == SystemRunStatus.SUCCESS
        assert len(status.coupons) == 4

        free = next(c for c in status.coupons if c.coupon_type == CouponType.FREE)
        safe = next(c for c in status.coupons if c.coupon_type == CouponType.SAFE)
        high = next(c for c in status.coupons if c.coupon_type == CouponType.HIGH_ODDS)

        assert free.created is True
        assert free.sent is True
        assert safe.created is True
        assert safe.sent is False
        assert high.created is False
        assert "Risk Engine" in (high.skip_reason or "")

    def test_no_matches_today(self, db_session, status_settings):
        status = StatusService(db_session, status_settings).get_daily_status(
            datetime(2099, 1, 1, tzinfo=timezone.utc).date()
        )
        assert status.no_matches_today is True

    def test_generation_error_status(self, db_session, status_settings):
        day = datetime(2026, 8, 12, 9, 0, tzinfo=timezone.utc)
        run = SystemRun(
            run_type=GENERATION_RUN_TYPE,
            status=SystemRunStatus.FAILED,
            error_message="Prediction Engine: timeout",
            started_at=day,
            finished_at=day,
        )
        db_session.add(run)
        db_session.flush()

        status = StatusService(db_session, status_settings).get_daily_status(day.date())
        assert status.generation_error is True
        assert status.failed_module == "Prediction Engine"
        assert status.error_detail == "timeout"
