"""Tests unitaires/intégration — ContextEngine."""

import pytest

from app.config.settings import Settings
from app.context.context_engine import ContextEngine
from app.context.exceptions import InsufficientStandingsError, MatchNotFoundError
from app.repositories.context_repository import ContextRepository
from tests.fixtures.context_helpers import seed_context_test_data


class TestContextEngine:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            context_title_race_positions=3,
            context_relegation_positions=3,
            context_european_positions=5,
            context_high_stakes_points_gap=6,
            context_derby_pairs="100:101",
        )

    def test_build_context_psg_amiens(self, db_session, settings):
        data = seed_context_test_data(db_session)
        engine = ContextEngine(db_session, settings)
        ctx = engine.build_context(data["target_match"].id)

        assert ctx.home_standing is not None
        assert ctx.away_standing is not None
        assert ctx.home_standing.team_name == "PSG"
        assert ctx.home_standing.position == 2
        assert ctx.away_standing.team_name == "Amiens"
        assert ctx.away_standing.position == 6
        assert ctx.get_factor("title_race") == 1.0
        assert ctx.get_factor("relegation_battle") == 1.0
        assert ctx.get_factor("high_stakes") == 1.0
        assert ctx.matches_remaining == 5
        assert ctx.data_quality == "HIGH"

    def test_persist_context(self, db_session, settings):
        data = seed_context_test_data(db_session)
        engine = ContextEngine(db_session, settings)
        engine.build_context(data["target_match"].id, persist=True)

        repo = ContextRepository(db_session)
        stored = repo.get_factors(data["target_match"].id)
        assert len(stored) > 0
        names = {f.factor_name for f in stored}
        assert "title_race" in names
        assert "relegation_battle" in names

    def test_flat_features(self, db_session, settings):
        data = seed_context_test_data(db_session)
        engine = ContextEngine(db_session, settings)
        ctx = engine.build_context(data["target_match"].id)
        flat = ctx.flat_features()
        assert flat["title_race"] == 1.0
        assert flat["home_position"] == 2
        assert flat["away_position"] == 6

    def test_derby_detection(self, db_session, settings):
        data = seed_context_test_data(db_session)
        settings.context_derby_pairs = "100:101"  # Leader FC vs PSG
        engine = ContextEngine(db_session, settings)

        from sqlalchemy import select
        from app.models.match import Match

        # Premier match terminé : Leader vs PSG (pas encore de classement)
        early_derby = db_session.scalar(
            select(Match).where(Match.external_match_id == 50000)
        )
        ctx = engine.build_context(early_derby.id)
        assert ctx.get_factor("derby") == 1.0
        assert ctx.get_factor("data_available") == 0.0

        # Match cible PSG vs Amiens — pas un derby
        ctx2 = engine.build_context(data["target_match"].id)
        assert ctx2.get_factor("derby") == 0.0

    def test_match_not_found(self, db_session, settings):
        engine = ContextEngine(db_session, settings)
        with pytest.raises(MatchNotFoundError):
            engine.build_context(99999)

    def test_as_of_leakage_rejected(self, db_session, settings):
        from datetime import datetime, timezone

        data = seed_context_test_data(db_session)
        engine = ContextEngine(db_session, settings)
        with pytest.raises(InsufficientStandingsError, match="data leakage"):
            engine.build_context(
                data["target_match"].id,
                as_of=datetime(2027, 1, 1, tzinfo=timezone.utc),
            )

    def test_to_dict(self, db_session, settings):
        data = seed_context_test_data(db_session)
        engine = ContextEngine(db_session, settings)
        ctx = engine.build_context(data["target_match"].id)
        d = ctx.to_dict()
        assert d["data_quality"] == "HIGH"
        assert d["home_standing"]["team_name"] == "PSG"

    def test_get_context_derby_pairs(self):
        s = Settings(_env_file=None, context_derby_pairs="100:101, 53:62")
        assert s.get_context_derby_pairs() == [(100, 101), (53, 62)]
