"""Tests unitaires/intégration — CouponGenerator."""

import pytest
from sqlalchemy import select

from app.config.settings import Settings
from app.coupons.candidate_builder import build_candidate
from app.coupons.coupon_generator import CouponGenerator
from app.database.enums import ConfidenceLevel, CouponStatus, CouponType, RiskDecision
from app.models.coupon import Coupon, CouponPrediction, CouponVersion
from app.prediction.constants import MARKET_1X2, SELECTION_HOME
from app.repositories.odds_repository import OddsRepository
from app.risk.risk_engine import RiskEngine
from app.value.odds_normalizer import normalize_odds_event
from app.value.value_engine import ValueEngine
from tests.fixtures.coupon_helpers import make_high_odds_pool, make_safe_pool, make_value_pool
from tests.fixtures.feature_helpers import seed_feature_test_data
from tests.fixtures.odds_helpers import ODDS_API_EVENT
from tests.unit.test_value_engine import _sample_prediction


class TestCouponGenerator:
    @pytest.fixture
    def settings(self):
        return Settings(
            _env_file=None,
            value_edge_min_threshold=0.05,
            coupon_safe_min_selections=3,
            coupon_value_min_selections=2,
            coupon_high_odds_min_selections=4,
            coupon_high_odds_min_combined=15.0,
            coupon_free_min_selections=3,
            risk_check_injuries=False,
            risk_check_lineups=False,
            risk_reject_stale_data=False,
        )

    def test_generate_all_coupon_types(self, db_session, settings):
        candidates = (
            make_safe_pool(4, start_id=1)
            + make_value_pool(3, start_id=11)
            + make_high_odds_pool(4, start_id=21)
            + make_safe_pool(5, start_id=31)
        )
        result = CouponGenerator(db_session, settings).generate(candidates)

        assert result.safe is not None and not result.safe.skipped
        assert result.value is not None and not result.value.skipped
        assert result.high_odds is not None and not result.high_odds.skipped
        assert result.free is not None and not result.free.skipped
        assert result.coupons_created == 4

    def test_generate_skips_when_insufficient(self, db_session, settings):
        candidates = make_safe_pool(1)
        result = CouponGenerator(db_session, settings).generate(candidates)
        assert result.coupons_created == 0
        assert result.safe is not None and result.safe.skipped

    def test_generate_premium_only(self, db_session, settings):
        candidates = make_safe_pool(4) + make_value_pool(2)
        result = CouponGenerator(db_session, settings).generate_premium_only(candidates)
        assert result.free is None
        assert result.coupons_created >= 1

    def test_generate_free_only(self, db_session, settings):
        candidates = make_safe_pool(4)
        result = CouponGenerator(db_session, settings).generate_free_only(candidates)
        assert result.safe is None
        assert result.value is None
        assert result.high_odds is None
        assert result.free is not None and not result.free.skipped

    def test_persist_coupons(self, db_session, settings):
        candidates = make_safe_pool(4)
        result = CouponGenerator(db_session, settings).generate(
            candidates,
            include_premium=False,
            include_free=True,
            persist=True,
        )
        assert result.free is not None
        assert result.free.coupon_id is not None

        coupon = db_session.get(Coupon, result.free.coupon_id)
        assert coupon is not None
        assert coupon.type == CouponType.FREE
        assert coupon.status == CouponStatus.DRAFT

        links = db_session.scalars(
            select(CouponPrediction).where(CouponPrediction.coupon_id == coupon.id)
        ).all()
        assert len(links) == len(result.free.candidates)

        versions = db_session.scalars(
            select(CouponVersion).where(CouponVersion.coupon_id == coupon.id)
        ).all()
        assert len(versions) == 1

    def test_build_candidate_from_pipeline(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        match_id = data["target_match"].id
        normalized = normalize_odds_event(ODDS_API_EVENT)
        OddsRepository(db_session).store_normalized_odds(match_id, normalized)

        pred = _sample_prediction(match_id)
        analysis = ValueEngine(db_session, settings).analyze(pred)
        assessment = RiskEngine(db_session, settings).assess(pred, analysis)
        opp = analysis.best_value
        assert opp is not None

        candidate = build_candidate(
            pred,
            opp,
            assessment,
            home_team="PSG",
            away_team="OM",
        )
        assert candidate is not None
        assert candidate.publishable
        assert candidate.match_id == match_id

    def test_build_candidate_rejects_non_publishable(self, db_session, settings):
        data = seed_feature_test_data(db_session)
        pred = _sample_prediction(data["target_match"].id)
        pred.confidence = ConfidenceLevel.LOW

        from app.value.schemas import ValueOpportunity

        opp = ValueOpportunity(
            match_id=pred.match_id,
            market_code=MARKET_1X2,
            selection=SELECTION_HOME,
            model_probability=0.68,
            implied_probability_raw=0.5,
            implied_probability=0.5,
            decimal_odds=2.0,
            value_edge=0.18,
            bookmaker="test",
            is_value=True,
        )
        from app.risk.schemas import SelectionRiskResult

        risk = SelectionRiskResult(
            match_id=pred.match_id,
            market_code=MARKET_1X2,
            selection=SELECTION_HOME,
            decision=RiskDecision.REJECT,
            confidence=ConfidenceLevel.LOW,
            publishable=False,
        )
        assert build_candidate(pred, opp, risk) is None

    def test_lazy_import(self):
        from app.coupons import CouponGenerator, CouponCandidate

        assert CouponGenerator is not None
        assert CouponCandidate is not None
