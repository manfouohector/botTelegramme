"""Tests unitaires — règles Risk Engine."""

import pytest

from app.config.settings import Settings
from app.database.enums import ConfidenceLevel, RiskDecision
from app.risk.constants import SEVERITY_HIGH, SEVERITY_MEDIUM
from app.risk.rules import aggregate_decision, evaluate_selection_factors, is_publishable
from app.risk.schemas import RiskFactorItem
from app.value.schemas import ValueOpportunity


class TestRiskRules:
    @pytest.fixture
    def settings(self):
        return Settings(_env_file=None, risk_reject_low_confidence=True)

    def test_aggregate_reject_on_high_severity(self, settings):
        factors = [RiskFactorItem("low_edge", "edge insuffisant", SEVERITY_HIGH)]
        assert aggregate_decision(factors, ConfidenceLevel.HIGH, settings) == RiskDecision.REJECT

    def test_aggregate_reject_low_confidence(self, settings):
        assert aggregate_decision([], ConfidenceLevel.LOW, settings) == RiskDecision.REJECT

    def test_aggregate_warning_on_medium(self, settings):
        factors = [RiskFactorItem("stale_data", "données anciennes", SEVERITY_MEDIUM)]
        assert aggregate_decision(factors, ConfidenceLevel.HIGH, settings) == RiskDecision.WARNING

    def test_aggregate_approve(self, settings):
        assert aggregate_decision([], ConfidenceLevel.HIGH, settings) == RiskDecision.APPROVE

    def test_is_publishable(self):
        assert is_publishable(RiskDecision.APPROVE) is True
        assert is_publishable(RiskDecision.WARNING) is True
        assert is_publishable(RiskDecision.REJECT) is False

    def test_no_value_factor(self, settings):
        factors = evaluate_selection_factors(None, None, settings=settings)
        assert any(f.severity == SEVERITY_MEDIUM for f in factors)

    def test_low_edge_rejects(self, settings):
        from app.value.schemas import MatchValueAnalysis

        opp = ValueOpportunity(
            match_id=1,
            market_code="1X2",
            selection="HOME",
            model_probability=0.55,
            implied_probability_raw=0.52,
            implied_probability=0.50,
            decimal_odds=2.0,
            value_edge=0.02,
            bookmaker="test",
            is_value=False,
        )
        factors = evaluate_selection_factors(
            opp, MatchValueAnalysis(match_id=1), settings=settings
        )
        assert any(f.severity == SEVERITY_HIGH for f in factors)
