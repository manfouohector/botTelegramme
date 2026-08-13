"""Tests unitaires/intégration — ValueEngine."""

from datetime import datetime, timezone

import pytest

from app.config.settings import Settings
from app.database.enums import ConfidenceLevel
from app.prediction.constants import MARKET_1X2, SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME
from app.prediction.schemas import MarketProbabilities, MatchPrediction
from app.repositories.odds_repository import OddsRepository
from app.value.exceptions import OddsNotFoundError
from app.value.odds_normalizer import normalize_odds_event
from app.value.value_engine import ValueEngine
from tests.fixtures.feature_helpers import seed_feature_test_data
from tests.fixtures.odds_helpers import ODDS_API_EVENT


def _sample_prediction(match_id: int) -> MatchPrediction:
    return MatchPrediction(
        match_id=match_id,
        external_match_id=99999,
        home_lambda=1.6,
        away_lambda=1.0,
        markets=[
            MarketProbabilities(
                MARKET_1X2,
                {SELECTION_HOME: 0.68, SELECTION_DRAW: 0.20, SELECTION_AWAY: 0.12},
                "ENSEMBLE",
            ),
        ],
        model_type="ENSEMBLE",
        model_version="1.0.0",
        confidence=ConfidenceLevel.HIGH,
    )


class TestValueEngine:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            value_edge_min_threshold=0.05,
            value_use_normalized_implied=True,
        )

    def test_analyze_detects_value(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        match_id = data["target_match"].id

        normalized = normalize_odds_event(ODDS_API_EVENT)
        OddsRepository(db_session).store_normalized_odds(match_id, normalized)

        engine = ValueEngine(db_session, settings)
        analysis = engine.analyze(_sample_prediction(match_id))

        assert analysis.has_value
        home = next(
            o for o in analysis.opportunities
            if o.market_code == MARKET_1X2 and o.selection == SELECTION_HOME
        )
        assert home.model_probability == pytest.approx(0.68)
        assert home.value_edge > 0.05
        assert home.is_value is True
        assert home.overround_normalized is True

    def test_no_odds_raises(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        engine = ValueEngine(db_session, settings)
        with pytest.raises(OddsNotFoundError):
            engine.analyze(_sample_prediction(data["target_match"].id))

    def test_best_value(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        normalized = normalize_odds_event(ODDS_API_EVENT)
        OddsRepository(db_session).store_normalized_odds(data["target_match"].id, normalized)

        analysis = ValueEngine(db_session, settings).analyze(
            _sample_prediction(data["target_match"].id)
        )
        assert analysis.best_value is not None
        assert analysis.best_value.value_edge == max(
            o.value_edge for o in analysis.opportunities if o.is_value
        )

    def test_to_dict(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        normalized = normalize_odds_event(ODDS_API_EVENT)
        OddsRepository(db_session).store_normalized_odds(data["target_match"].id, normalized)
        analysis = ValueEngine(db_session, settings).analyze(
            _sample_prediction(data["target_match"].id)
        )
        d = analysis.to_dict()
        assert "opportunities" in d
        assert d["has_value"] is True
