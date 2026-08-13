"""Tests unitaires/intégration — FeatureEngine."""

from datetime import datetime, timezone

import pytest

from app.config.settings import Settings
from app.features.exceptions import InsufficientDataError, MatchNotFoundError
from app.features.feature_engine import FeatureEngine
from app.repositories.match_history_repository import MatchHistoryRepository
from tests.fixtures.feature_helpers import seed_feature_test_data


class TestMatchHistoryRepository:
    def test_no_future_leakage(self, db_session):
        data = seed_feature_test_data(db_session)
        repo = MatchHistoryRepository(db_session)

        records = repo.get_team_finished_matches(
            data["psg"].id,
            data["target_match"].scheduled_at,
            season_id=data["season"].id,
            limit=10,
        )
        # Ne doit pas inclure le match futur (5-0) ni le match cible
        assert all(r.scheduled_at < data["target_match"].scheduled_at for r in records)
        assert len(records) == 6  # 5 matchs saison + 1 H2H dédié

    def test_h2h_excludes_future(self, db_session):
        data = seed_feature_test_data(db_session)
        repo = MatchHistoryRepository(db_session)

        h2h = repo.get_h2h_matches(
            data["psg"].id,
            data["om"].id,
            data["target_match"].scheduled_at,
            limit=10,
        )
        assert len(h2h) == 2  # 2-1 + 1-1, pas le futur 5-0
        assert sum(m.home_score + m.away_score for m in h2h) == 5  # 3 + 2


class TestFeatureEngine:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            feature_form_window=5,
            feature_h2h_window=5,
            feature_min_matches=3,
        )

    def test_build_features_success(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)

        features = engine.build_features(data["target_match"].id)

        assert features.match_id == data["target_match"].id
        assert features.home_form.matches_played == 5  # fenêtre limitée à 5
        assert features.home_form.wins == 4
        assert features.away_form.wins == 1
        assert features.away_form.draws == 2
        assert features.h2h.matches_played == 2
        assert features.h2h.home_wins == 1
        assert features.h2h.draws == 1
        assert features.data_quality == "HIGH"

    def test_home_form_points(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)
        features = engine.build_features(data["target_match"].id)

        # PSG: 3+3+1+3+3 = 13 points / 5 = 2.6
        assert features.home_form.points == 13
        assert features.home_form.points_per_match == 2.6

    def test_flat_features(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)
        features = engine.build_features(data["target_match"].id)

        flat = features.flat_features()
        assert "home_form_points_per_match" in flat
        assert "away_form_points_per_match" in flat
        assert "h2h_home_wins" in flat
        assert flat["h2h_home_wins"] == 1

    def test_to_dict_serializable(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)
        features = engine.build_features(data["target_match"].id)

        d = features.to_dict()
        assert d["data_quality"] == "HIGH"
        assert "home_form" in d
        assert d["home_form"]["wins"] == 4

    def test_match_not_found(self, db_session, settings):
        engine = FeatureEngine(db_session, settings)
        with pytest.raises(MatchNotFoundError):
            engine.build_features(99999)

    def test_as_of_leakage_rejected(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)

        future_as_of = datetime(2026, 8, 25, tzinfo=timezone.utc)
        with pytest.raises(InsufficientDataError, match="data leakage"):
            engine.build_features(data["target_match"].id, as_of=future_as_of)

    def test_low_data_quality(self, db_session, settings):
        settings.feature_min_matches = 10
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)
        features = engine.build_features(data["target_match"].id)
        assert features.data_quality == "MEDIUM"

    def test_attack_defense_shots(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)
        features = engine.build_features(data["target_match"].id)
        assert features.home_attack_defense.stats_available is True
        assert features.home_attack_defense.shots_per_match is not None

    def test_build_features_batch(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = FeatureEngine(db_session, settings)
        results = engine.build_features_batch([data["target_match"].id, 99999])
        assert len(results) == 1
