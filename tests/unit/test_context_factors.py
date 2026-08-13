"""Tests unitaires — facteurs de contexte."""

import pytest

from app.config.settings import Settings
from app.context.calculators.factors import compute_context_factors
from app.context.schemas import TeamStanding


def _standing(team_id, position, points, played=30):
    return TeamStanding(
        team_id=team_id,
        team_external_id=team_id * 10,
        team_name=f"Team {team_id}",
        position=position,
        played=played,
        wins=0,
        draws=0,
        losses=0,
        points=points,
        goals_for=0,
        goals_against=0,
        goal_difference=0,
    )


class TestContextFactors:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            context_title_race_positions=3,
            context_relegation_positions=3,
            context_european_positions=5,
            context_high_stakes_points_gap=6,
        )

    def test_title_and_relegation_flags(self, settings):
        home = _standing(1, 2, 61)
        away = _standing(2, 18, 24)
        factors = compute_context_factors(
            home_standing=home,
            away_standing=away,
            total_teams=18,
            matches_remaining=5,
            is_derby=False,
            is_cup=False,
            settings=settings,
            leader_points=66,
        )
        by_name = {f.name: f.value for f in factors}
        assert by_name["home_title_race"] == 1.0
        assert by_name["away_relegation_battle"] == 1.0
        assert by_name["title_race"] == 1.0
        assert by_name["relegation_battle"] == 1.0
        assert by_name["high_stakes"] == 1.0
        assert by_name["matches_remaining"] == 5.0
        assert by_name["points_gap"] == 37.0

    def test_derby_flag(self, settings):
        home = _standing(1, 5, 40)
        away = _standing(2, 6, 38)
        factors = compute_context_factors(
            home_standing=home,
            away_standing=away,
            total_teams=10,
            matches_remaining=3,
            is_derby=True,
            is_cup=False,
            settings=settings,
            leader_points=50,
        )
        by_name = {f.name: f.value for f in factors}
        assert by_name["derby"] == 1.0
        assert by_name["high_stakes"] == 1.0

    def test_cup_match(self, settings):
        home = _standing(1, 8, 30)
        away = _standing(2, 9, 28)
        factors = compute_context_factors(
            home_standing=home,
            away_standing=away,
            total_teams=12,
            matches_remaining=1,
            is_derby=False,
            is_cup=True,
            settings=settings,
            leader_points=45,
        )
        by_name = {f.name: f.value for f in factors}
        assert by_name["cup_match"] == 1.0
        assert by_name["high_stakes"] == 1.0

    def test_insufficient_data(self, settings):
        factors = compute_context_factors(
            home_standing=None,
            away_standing=None,
            total_teams=0,
            matches_remaining=0,
            is_derby=False,
            is_cup=False,
            settings=settings,
        )
        assert factors[0].name == "matches_remaining"
        assert any(f.name == "data_available" and f.value == 0.0 for f in factors)
