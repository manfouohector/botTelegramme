"""Tests d'intégration — admin /status et /history."""

from datetime import datetime, timezone

from app.services.history_service import HistoryService
from app.services.status_service import StatusService
from tests.fixtures.generation_helpers import seed_history_day, seed_status_day


class TestAdminWorkflow:
    def test_status_after_seeded_generation(self, db_session, integration_settings):
        day = datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc)
        seed_status_day(db_session, day=day, timezone_name="UTC")

        status = StatusService(db_session, integration_settings).get_daily_status(day.date())
        assert status.system_run_id is not None
        assert status.matches_analyzed == 18
        assert status.published is True

        free = next(c for c in status.coupons if c.coupon_type.value == "FREE")
        assert free.created is True
        assert free.sent is True

    def test_history_after_settled_day(self, db_session, integration_settings):
        day = datetime(2026, 8, 19, 18, 0, tzinfo=timezone.utc)
        seed_history_day(db_session, day=day)

        history = HistoryService(db_session, integration_settings).get_history(day.date())
        assert history.total_won + history.total_lost > 0
        assert len(history.by_type) == 4

        parsed = HistoryService(db_session, integration_settings).parse_date_arg("2026-08-19")
        assert parsed == day.date()
