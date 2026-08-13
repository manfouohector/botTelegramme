"""Tests unitaires/intégration — PredictionEngine."""

import pytest

from app.config.settings import Settings
from app.database.enums import ConfidenceLevel
from app.prediction.constants import MARKET_1X2, MARKET_BTTS, MARKET_OU25, MODEL_ENSEMBLE
from app.prediction.exceptions import MatchNotFoundError
from app.prediction.prediction_engine import PredictionEngine
from app.repositories.prediction_repository import PredictionRepository
from tests.fixtures.feature_helpers import seed_feature_test_data


class TestPredictionEngine:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            prediction_enable_ml=False,
            prediction_enable_dixon_coles=True,
            prediction_min_matches=3,
            feature_min_matches=3,
            feature_form_window=5,
        )

    def test_build_prediction_success(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = PredictionEngine(db_session, settings)
        pred = engine.build_prediction(data["target_match"].id)

        assert pred.home_lambda > 0
        assert pred.away_lambda > 0
        m1x2 = pred.get_market(MARKET_1X2)
        assert m1x2 is not None
        assert abs(sum(m1x2.probabilities.values()) - 1.0) < 1e-6
        assert pred.get_probability(MARKET_1X2, "HOME") is not None
        assert pred.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW)

    def test_all_markets_present(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = PredictionEngine(db_session, settings)
        pred = engine.build_prediction(data["target_match"].id)
        codes = {m.market_code for m in pred.markets}
        assert MARKET_1X2 in codes
        assert MARKET_BTTS in codes
        assert MARKET_OU25 in codes

    def test_home_favorite_psg(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = PredictionEngine(db_session, settings)
        pred = engine.build_prediction(data["target_match"].id)
        home_prob = pred.get_probability(MARKET_1X2, "HOME") or 0
        away_prob = pred.get_probability(MARKET_1X2, "AWAY") or 0
        assert home_prob > away_prob

    def test_flat_probabilities(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = PredictionEngine(db_session, settings)
        pred = engine.build_prediction(data["target_match"].id)
        flat = pred.flat_probabilities()
        assert "1X2_HOME" in flat
        assert "home_lambda" in flat

    def test_persist_prediction(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = PredictionEngine(db_session, settings)
        engine.build_prediction(data["target_match"].id, persist=True)
        repo = PredictionRepository(db_session)
        rows = repo.get_predictions_for_match(data["target_match"].id)
        assert len(rows) >= 3  # 1X2(3) + BTTS(2) + OU25(2) = 7
        assert all(row.probability is not None for row in rows)

    def test_match_not_found(self, db_session, settings):
        engine = PredictionEngine(db_session, settings)
        with pytest.raises(MatchNotFoundError):
            engine.build_prediction(99999)

    def test_to_dict(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = PredictionEngine(db_session, settings)
        pred = engine.build_prediction(data["target_match"].id)
        d = pred.to_dict()
        assert d["model_version"]
        assert "markets" in d
        assert "features_snapshot" in d

    def test_disabled_markets(self, db_session, settings):
        settings.prediction_markets = "1X2"
        data = seed_feature_test_data(db_session)
        engine = PredictionEngine(db_session, settings)
        pred = engine.build_prediction(data["target_match"].id)
        assert len(pred.markets) == 1

    def test_ml_ensemble_when_enough_samples(self, db_session):
        from datetime import datetime, timedelta, timezone

        from app.database.enums import DataStatus, MatchStatus
        from app.models.football import Competition, Season, Team
        from app.models.match import Match, MatchStatistic

        settings = Settings(
            _env_file=None,
            prediction_enable_ml=True,
            prediction_ml_min_samples=10,
            prediction_min_matches=2,
            feature_min_matches=2,
            feature_form_window=3,
            xg_min_training_samples=10,
            xg_min_matches=2,
        )
        comp = Competition(external_id=501, name="Test League", country="Test")
        db_session.add(comp)
        db_session.flush()
        season = Season(competition_id=comp.id, external_id=2025, name="2025/2026", is_current=True)
        db_session.add(season)
        db_session.flush()
        home = Team(external_id=701, name="Alpha", short_name="ALP")
        away = Team(external_id=702, name="Beta", short_name="BET")
        db_session.add_all([home, away])
        db_session.flush()

        base = datetime(2026, 2, 1, 15, 0, tzinfo=timezone.utc)
        ext = 80000
        results = [
            (2, 1), (1, 0), (3, 1), (2, 2), (1, 1), (2, 0),
            (0, 1), (1, 2), (3, 0), (2, 1), (1, 0), (4, 2),
        ]
        for i, (hs, aws) in enumerate(results):
            m = Match(
                external_match_id=ext,
                competition_id=comp.id,
                season_id=season.id,
                home_team_id=home.id,
                away_team_id=away.id,
                scheduled_at=base + timedelta(days=i * 2),
                status=MatchStatus.FINISHED,
                home_score=hs,
                away_score=aws,
                data_status=DataStatus.FRESH,
            )
            db_session.add(m)
            db_session.flush()
            db_session.add(MatchStatistic(match_id=m.id, team_id=home.id, stats={"type_42": 12, "type_49": 5}))
            db_session.add(MatchStatistic(match_id=m.id, team_id=away.id, stats={"type_42": 9, "type_49": 3}))
            ext += 1

        target = Match(
            external_match_id=ext,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=base + timedelta(days=30),
            status=MatchStatus.SCHEDULED,
            data_status=DataStatus.FRESH,
        )
        db_session.add(target)
        db_session.flush()

        engine = PredictionEngine(db_session, settings)
        pred = engine.build_prediction(target.id)
        assert pred.model_type == MODEL_ENSEMBLE
        assert pred.metadata["ml_trained"] is True
