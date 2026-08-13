"""Tests unitaires — calculateur de forme."""

from app.features.calculators.form import compute_form_features
from app.features.records import TeamMatchRecord


def _record(scored: int, conceded: int, match_id: int = 1) -> TeamMatchRecord:
    from datetime import datetime, timezone

    return TeamMatchRecord(
        match_id=match_id,
        scheduled_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        team_id=1,
        opponent_id=2,
        is_home=True,
        goals_scored=scored,
        goals_conceded=conceded,
        stats={},
    )


class TestFormCalculator:
    def test_empty_records(self):
        f = compute_form_features(1, [])
        assert f.matches_played == 0
        assert f.points == 0

    def test_win_draw_loss(self):
        records = [_record(2, 1), _record(1, 1), _record(0, 1)]
        f = compute_form_features(1, records)
        assert f.wins == 1
        assert f.draws == 1
        assert f.losses == 1
        assert f.points == 4
        assert f.points_per_match == 4 / 3

    def test_goal_averages(self):
        records = [_record(3, 0), _record(2, 1)]
        f = compute_form_features(1, records)
        assert f.goals_scored == 5
        assert f.goals_conceded == 1
        assert f.goals_scored_per_match == 2.5
        assert f.clean_sheets == 1

    def test_win_streak(self):
        records = [_record(0, 1), _record(2, 0), _record(1, 0)]
        f = compute_form_features(1, records)
        assert f.win_streak == 0  # match le plus récent = défaite

    def test_win_streak_from_start(self):
        records = [_record(2, 0), _record(1, 0)]
        f = compute_form_features(1, records)
        assert f.win_streak == 2
        assert f.unbeaten_streak == 2
