"""Tests unitaires — extraction stats tirs."""

from app.features.records import TeamMatchRecord
from app.xg.shot_stats import average_shot_stats, extract_shot_stats, records_with_shot_data


class TestShotStats:
    def test_extract_shots(self):
        ss = extract_shot_stats({"type_42": 12, "type_49": 5})
        assert ss.shots == 12.0
        assert ss.shots_on_target == 5.0
        assert ss.has_data is True

    def test_extract_empty(self):
        ss = extract_shot_stats({})
        assert ss.has_data is False

    def test_average_shot_stats(self):
        from datetime import datetime, timezone

        rec = lambda s, t: TeamMatchRecord(
            match_id=1, scheduled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            team_id=1, opponent_id=2, is_home=True, goals_scored=1, goals_conceded=0,
            stats={"type_42": s, "type_49": t},
        )
        avg = average_shot_stats([rec(10, 4), rec(14, 6)])
        assert avg.shots == 12.0
        assert avg.shots_on_target == 5.0

    def test_records_with_shot_data(self):
        from datetime import datetime, timezone

        r1 = TeamMatchRecord(
            match_id=1, scheduled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            team_id=1, opponent_id=2, is_home=True, goals_scored=1, goals_conceded=0,
            stats={"type_42": 10},
        )
        r2 = TeamMatchRecord(
            match_id=2, scheduled_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            team_id=1, opponent_id=2, is_home=True, goals_scored=0, goals_conceded=0,
            stats={},
        )
        assert len(records_with_shot_data([r1, r2])) == 1
