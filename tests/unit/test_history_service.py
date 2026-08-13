"""Tests unitaires — HistoryService."""

from datetime import datetime, timezone

import pytest

from app.config.settings import Settings
from app.database.enums import CouponType
from app.services.history_service import HistoryService
from tests.fixtures.generation_helpers import seed_history_day


@pytest.fixture
def history_settings():
    return Settings(_env_file=None, timezone="UTC")


class TestHistoryService:
    def test_history_for_specific_date(self, db_session, history_settings):
        day = datetime(2026, 8, 11, 18, 0, tzinfo=timezone.utc)
        seeded = seed_history_day(db_session, day=day)

        summary = HistoryService(db_session, history_settings).get_history(seeded["day"])
        assert summary.has_data is True
        assert summary.total_won == 13
        assert summary.total_lost == 3

        by_type = {entry.coupon_type: entry for entry in summary.by_type}
        assert by_type[CouponType.FREE].display_ratio == "3/3"
        assert by_type[CouponType.VALUE].display_ratio == "2/3"
        assert by_type[CouponType.HIGH_ODDS].display_ratio == "4/6"

    def test_latest_settled_day_default(self, db_session, history_settings):
        day = datetime(2026, 8, 11, 18, 0, tzinfo=timezone.utc)
        seed_history_day(db_session, day=day)

        summary = HistoryService(db_session, history_settings).get_history()
        assert summary.target_date == day.date()

    def test_parse_date_arg(self):
        assert HistoryService.parse_date_arg("2026-08-11") == datetime(2026, 8, 11).date()
        assert HistoryService.parse_date_arg("invalid") is None
        assert HistoryService.parse_date_arg(None) is None

    def test_empty_history(self, db_session, history_settings):
        summary = HistoryService(db_session, history_settings).get_history(
            datetime(2099, 1, 1).date()
        )
        assert summary.has_data is False
