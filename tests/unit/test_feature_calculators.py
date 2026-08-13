"""Tests unitaires — calculateurs home/away, attack/defense, h2h."""

from datetime import datetime, timezone

from app.features.calculators.attack_defense import compute_attack_defense_features
from app.features.calculators.h2h import compute_h2h_features
from app.features.calculators.home_away import compute_home_away_features
from app.database.enums import MatchStatus
from app.models.match import Match
from app.features.records import TeamMatchRecord


def _rec(scored, conceded, stats=None):
    return TeamMatchRecord(
        match_id=1,
        scheduled_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        team_id=1,
        opponent_id=2,
        is_home=True,
        goals_scored=scored,
        goals_conceded=conceded,
        stats=stats or {},
    )


class TestHomeAwayCalculator:
    def test_home_performance(self):
        f = compute_home_away_features(1, [_rec(2, 0), _rec(1, 1)], "home")
        assert f.venue == "home"
        assert f.matches_played == 2
        assert f.wins == 1
        assert f.draws == 1


class TestAttackDefenseCalculator:
    def test_goals_only(self):
        f = compute_attack_defense_features([_rec(3, 1), _rec(1, 0)])
        assert f.goals_scored_per_match == 2.0
        assert f.goals_conceded_per_match == 0.5
        assert f.stats_available is False

    def test_with_shots_stats(self):
        f = compute_attack_defense_features([
            _rec(2, 1, {"type_42": 10, "type_49": 4}),
            _rec(1, 0, {"type_42": 14, "type_49": 6}),
        ])
        assert f.stats_available is True
        assert f.shots_per_match == 12.0
        assert f.shots_on_target_per_match == 5.0


class TestH2HCalculator:
    def _match(self, home_id, away_id, hs, aws, mid=1):
        return Match(
            id=mid,
            external_match_id=mid,
            competition_id=1,
            season_id=1,
            home_team_id=home_id,
            away_team_id=away_id,
            scheduled_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            status=MatchStatus.FINISHED,
            home_score=hs,
            away_score=aws,
        )

    def test_h2h_perspective(self):
        # PSG (100) vs OM (101), PSG won 2-1 at home
        m = self._match(100, 101, 2, 1)
        f = compute_h2h_features([m], perspective_home_team_id=100, perspective_away_team_id=101)
        assert f.matches_played == 1
        assert f.home_wins == 1
        assert f.avg_total_goals == 3.0

    def test_empty_h2h(self):
        f = compute_h2h_features([], 100, 101)
        assert f.matches_played == 0
