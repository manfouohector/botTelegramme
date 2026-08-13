"""Tests unitaires — calcul classement."""

from datetime import datetime, timezone

from app.context.standings import StandingsCalculator
from tests.fixtures.context_helpers import seed_context_test_data


class TestStandingsCalculator:
    def test_compute_standings(self, db_session):
        data = seed_context_test_data(db_session)
        calc = StandingsCalculator(db_session)

        snapshot = calc.compute(
            data["season"].id,
            data["target_match"].scheduled_at,
            competition_id=data["competition"].id,
        )
        ranked = snapshot.sorted_by_rank()
        assert snapshot.total_teams == 6
        assert ranked[0].team_name == "Leader FC"
        assert ranked[1].team_name == "PSG"

    def test_no_leakage_future_matches(self, db_session):
        data = seed_context_test_data(db_session)
        calc = StandingsCalculator(db_session)

        # Classement avant le premier match terminé
        early = datetime(2025, 12, 1, tzinfo=timezone.utc)
        snapshot = calc.compute(data["season"].id, early)
        assert snapshot.total_teams == 0

    def test_count_remaining_matches(self, db_session):
        data = seed_context_test_data(db_session)
        calc = StandingsCalculator(db_session)
        remaining = calc.count_remaining_matches(
            data["season"].id,
            data["target_match"].scheduled_at,
        )
        assert remaining == 5
