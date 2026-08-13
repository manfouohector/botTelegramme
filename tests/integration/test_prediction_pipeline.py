"""Tests d'intégration — pipeline prédiction complet."""

from app.calibration.calibration_engine import CalibrationEngine
from app.context.context_engine import ContextEngine
from app.coupons.candidate_builder import build_candidates_from_analyses
from app.features.feature_engine import FeatureEngine
from app.prediction.constants import MARKET_1X2
from app.prediction.prediction_engine import PredictionEngine
from app.risk.risk_engine import RiskEngine
from app.value.value_engine import ValueEngine
from app.xg.xg_engine import XGEngine


class TestPredictionPipeline:
    def test_full_analysis_chain(self, db_session, integration_settings, seeded_match_day):
        """Feature → Context → xG → Prediction → Value → Risk sur données réelles."""
        match_id = seeded_match_day["match"].id

        features = FeatureEngine(db_session, integration_settings).build_features(match_id)
        assert features.home_form.matches_played >= integration_settings.feature_min_matches

        context = ContextEngine(db_session, integration_settings).build_context(match_id)
        assert context.home_standing is not None
        assert context.home_standing.team_id == seeded_match_day["psg"].id

        xg = XGEngine(db_session, integration_settings).build_xg(match_id)
        assert xg.match_id == match_id
        assert xg.model_type

        prediction = PredictionEngine(db_session, integration_settings).build_prediction(match_id)
        assert prediction.get_market(MARKET_1X2) is not None

        calibration = CalibrationEngine(
            db_session,
            integration_settings,
            prediction_engine=PredictionEngine(db_session, integration_settings),
        )
        calibrated = calibration.calibrate(prediction)

        value = ValueEngine(db_session, integration_settings).analyze(calibrated)
        assert len(value.opportunities) >= 1

        risk = RiskEngine(db_session, integration_settings).assess(calibrated, value)
        assert risk.decision is not None
        assert len(risk.selections) >= 1

    def test_candidates_from_pipeline(self, db_session, integration_settings, seeded_match_day):
        """Le builder produit des candidats publishables depuis le pipeline."""
        match_id = seeded_match_day["match"].id
        engine = PredictionEngine(db_session, integration_settings)
        calibration = CalibrationEngine(db_session, integration_settings, prediction_engine=engine)

        prediction = engine.build_prediction(match_id)
        calibrated = calibration.calibrate(prediction)
        value = ValueEngine(db_session, integration_settings).analyze(calibrated)
        risk = RiskEngine(db_session, integration_settings).assess(calibrated, value)

        candidates = build_candidates_from_analyses(
            db_session,
            [(calibrated.raw, value, risk)],
        )
        assert len(candidates) >= 1
        assert all(c.decimal_odds > 1.0 for c in candidates)
