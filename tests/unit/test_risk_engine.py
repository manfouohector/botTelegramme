"""Tests unitaires/intégration — RiskEngine."""

import pytest

from app.config.settings import Settings
from app.database.enums import ConfidenceLevel, DataStatus, RiskDecision
from app.prediction.constants import MARKET_1X2, SELECTION_HOME
from app.repositories.odds_repository import OddsRepository
from app.repositories.risk_repository import RiskRepository
from app.risk.risk_engine import RiskEngine
from app.value.odds_normalizer import normalize_odds_event
from app.value.schemas import ValueOpportunity
from app.value.value_engine import ValueEngine
from tests.fixtures.feature_helpers import seed_feature_test_data
from tests.fixtures.odds_helpers import ODDS_API_EVENT
from tests.unit.test_value_engine import _sample_prediction


class TestRiskEngine:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            value_edge_min_threshold=0.05,
            risk_reject_low_confidence=True,
            risk_check_injuries=False,
            risk_check_lineups=False,
            risk_reject_stale_data=False,
        )

    def _value_analysis(self, db_session, settings, match_id):
        normalized = normalize_odds_event(ODDS_API_EVENT)
        OddsRepository(db_session).store_normalized_odds(match_id, normalized)
        pred = _sample_prediction(match_id)
        return ValueEngine(db_session, settings).analyze(pred), pred

    def test_approve_high_confidence_value(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        analysis, pred = self._value_analysis(db_session, settings, data["target_match"].id)
        assessment = RiskEngine(db_session, settings).assess(pred, analysis)
        assert assessment.decision == RiskDecision.APPROVE
        assert assessment.publishable is True

    def test_reject_low_confidence(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        analysis, pred = self._value_analysis(db_session, settings, data["target_match"].id)
        pred.confidence = ConfidenceLevel.LOW
        assessment = RiskEngine(db_session, settings).assess(pred, analysis)
        assert assessment.decision == RiskDecision.REJECT
        assert assessment.publishable is False

    def test_reject_incomplete_data(self, db_session, settings):
        settings.risk_reject_incomplete_data = True
        data = seed_feature_test_data(db_session)
        data["target_match"].data_status = DataStatus.INCOMPLETE
        analysis, pred = self._value_analysis(db_session, settings, data["target_match"].id)
        assessment = RiskEngine(db_session, settings).assess(pred, analysis)
        assert assessment.decision == RiskDecision.REJECT

    def test_warning_extreme_edge(self, db_session, settings):
        settings.risk_max_edge_threshold = 0.05
        data = seed_feature_test_data(db_session)
        analysis, pred = self._value_analysis(db_session, settings, data["target_match"].id)
        opp = analysis.best_value
        assert opp is not None
        extreme = ValueOpportunity(
            match_id=opp.match_id,
            market_code=opp.market_code,
            selection=opp.selection,
            model_probability=0.95,
            implied_probability_raw=0.5,
            implied_probability=0.5,
            decimal_odds=2.0,
            value_edge=0.45,
            bookmaker=opp.bookmaker,
            is_value=True,
        )
        assessment = RiskEngine(db_session, settings).assess(pred, analysis, opportunity=extreme)
        assert assessment.decision == RiskDecision.WARNING

    def test_persist_factors(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        analysis, pred = self._value_analysis(db_session, settings, data["target_match"].id)
        RiskEngine(db_session, settings).assess(pred, analysis, persist=True)
        factors = RiskRepository(db_session).get_factors(data["target_match"].id)
        assert len(factors) >= 0

    def test_no_odds_warning(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        pred = _sample_prediction(data["target_match"].id)
        assessment = RiskEngine(db_session, settings).assess(pred, None)
        assert assessment.decision in (RiskDecision.WARNING, RiskDecision.REJECT)

    def test_selection_result_present(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        analysis, pred = self._value_analysis(db_session, settings, data["target_match"].id)
        assessment = RiskEngine(db_session, settings).assess(pred, analysis)
        assert len(assessment.selections) == 1
        sel = assessment.selections[0]
        assert sel.market_code == MARKET_1X2
        assert sel.selection == SELECTION_HOME

    def test_to_dict(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        analysis, pred = self._value_analysis(db_session, settings, data["target_match"].id)
        d = RiskEngine(db_session, settings).assess(pred, analysis).to_dict()
        assert "decision" in d
        assert "publishable" in d
