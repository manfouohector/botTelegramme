"""Prediction Engine — Poisson/Dixon-Coles + ML optionnel."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.context.context_engine import ContextEngine
from app.context.schemas import MatchContext
from app.features.exceptions import InsufficientDataError as FeatureInsufficientDataError
from app.features.exceptions import MatchNotFoundError as FeatureMatchNotFoundError
from app.features.feature_engine import FeatureEngine
from app.features.schemas import MatchFeatures
from app.models.match import Match
from app.repositories.prediction_data_repository import PredictionDataRepository
from app.repositories.prediction_repository import PredictionRepository
from app.utils.logging import get_logger, log_event
from app.xg.exceptions import InsufficientXGDataError, MatchNotFoundError as XGMatchNotFoundError
from app.xg.schemas import MatchXG
from app.xg.xg_engine import XGEngine

from app.prediction.confidence import assess_confidence
from app.prediction.constants import (
    ENGINE_VERSION,
    MARKET_1X2,
    MODEL_ENSEMBLE,
    MODEL_ML,
)
from app.prediction.dixon_coles import apply_dixon_coles
from app.prediction.exceptions import (
    InsufficientPredictionDataError,
    MatchNotFoundError,
)
from app.prediction.lambdas import estimate_lambdas
from app.prediction.markets import derive_markets, ensemble_1x2, poisson_model_label
from app.prediction.ml_model import OutcomeMLModel
from app.prediction.poisson import build_score_matrix
from app.prediction.schemas import MarketProbabilities, MatchPrediction

logger = get_logger(__name__)


class PredictionEngine:
    """
    Produit des probabilités pour un match.

    Pipeline :
    Features + Context + xG → lambdas → Poisson/Dixon-Coles → marchés
    + ML 1X2 optionnel → ensemble simple
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.features_engine = FeatureEngine(session, self.settings)
        self.context_engine = ContextEngine(session, self.settings)
        self.xg_engine = XGEngine(session, self.settings)
        self.prediction_data = PredictionDataRepository(session)
        self.prediction_repo = PredictionRepository(session)

    def build_prediction(
        self,
        match_id: int,
        *,
        as_of: datetime | None = None,
        persist: bool = False,
    ) -> MatchPrediction:
        features = self._build_features(match_id, as_of)
        reference = features.as_of

        context = self.context_engine.build_context(match_id, as_of=reference, persist=False)
        xg = self._build_xg_safe(match_id, reference)

        home_lambda, away_lambda = estimate_lambdas(features, xg, self.settings)

        matrix = build_score_matrix(
            home_lambda,
            away_lambda,
            max_goals=self.settings.prediction_max_goals,
        )
        poisson_label = poisson_model_label(dixon_coles_enabled=self.settings.prediction_enable_dixon_coles)
        if self.settings.prediction_enable_dixon_coles:
            matrix = apply_dixon_coles(
                matrix,
                home_lambda,
                away_lambda,
                self.settings.prediction_dixon_coles_rho,
            )

        enabled = self.settings.get_prediction_markets()
        markets = derive_markets(matrix, model_type=poisson_label, enabled_markets=enabled)

        ml_model = OutcomeMLModel()
        ml_probs: dict[str, float] | None = None
        if self.settings.prediction_enable_ml:
            ml_probs = self._train_and_predict_ml(
                match_id, features, context, xg, reference, ml_model
            )

        model_type = poisson_label
        if ml_probs and MARKET_1X2 in enabled:
            poisson_1x2 = self._get_1x2_probs(markets)
            blended = ensemble_1x2(
                poisson_1x2,
                ml_probs,
                poisson_weight=self.settings.prediction_ensemble_poisson_weight,
            )
            markets = self._replace_1x2_market(markets, blended, MODEL_ENSEMBLE)
            model_type = MODEL_ENSEMBLE

        poisson_1x2 = self._get_1x2_probs(markets)
        confidence = assess_confidence(
            features,
            xg,
            ml_trained=ml_model.trained,
            poisson_1x2=poisson_1x2 if poisson_1x2 else {},
            ml_1x2=ml_probs,
            settings=self.settings,
        )

        snapshot = self._build_features_snapshot(features, context, xg)

        result = MatchPrediction(
            match_id=features.match_id,
            external_match_id=features.external_match_id,
            home_lambda=home_lambda,
            away_lambda=away_lambda,
            markets=markets,
            model_type=model_type,
            model_version=ENGINE_VERSION,
            confidence=confidence,
            features_snapshot=snapshot,
            metadata={
                "poisson_model": poisson_label,
                "ml_trained": ml_model.trained,
                "ml_sample_size": ml_model.sample_size,
                "enabled_markets": list(enabled),
                "data_quality_features": features.data_quality,
                "data_quality_xg": xg.data_quality if xg else "UNAVAILABLE",
            },
        )

        log_event(
            logger,
            "PREDICTION_BUILT",
            match_id=match_id,
            model_type=model_type,
            confidence=confidence.value,
            home_lambda=round(home_lambda, 3),
            away_lambda=round(away_lambda, 3),
        )

        if persist:
            self.prediction_repo.save_prediction(result)

        return result

    def _build_features(self, match_id: int, as_of: datetime | None) -> MatchFeatures:
        try:
            return self.features_engine.build_features(match_id, as_of=as_of)
        except FeatureMatchNotFoundError as exc:
            raise MatchNotFoundError(str(exc)) from exc
        except FeatureInsufficientDataError as exc:
            raise InsufficientPredictionDataError(str(exc)) from exc

    def _build_xg_safe(self, match_id: int, as_of: datetime) -> MatchXG | None:
        try:
            return self.xg_engine.build_xg(match_id, as_of=as_of)
        except (XGMatchNotFoundError, InsufficientXGDataError):
            return None

    def _train_and_predict_ml(
        self,
        match_id: int,
        target_features: MatchFeatures,
        target_context: MatchContext,
        target_xg: MatchXG | None,
        reference: datetime,
        ml_model: OutcomeMLModel,
    ) -> dict[str, float] | None:
        match = self.session.scalar(select(Match).where(Match.id == match_id))
        if match is None:
            return None

        training_matches = self.prediction_data.get_season_finished_matches(
            match.season_id,
            reference,
            competition_id=match.competition_id,
            exclude_match_id=match_id,
        )

        feature_rows: list[dict[str, float | int | bool]] = []
        labels: list[str] = []

        for hist_match in training_matches:
            try:
                hist_features = self.features_engine.build_features(
                    hist_match.id, as_of=hist_match.scheduled_at
                )
                hist_context = self.context_engine.build_context(
                    hist_match.id, as_of=hist_match.scheduled_at, persist=False
                )
                hist_xg = self._build_xg_safe(hist_match.id, hist_match.scheduled_at)
                feature_rows.append(
                    self._build_combined_flat(hist_features, hist_context, hist_xg)
                )
                labels.append(self.prediction_data.match_outcome(hist_match))
            except (FeatureMatchNotFoundError, FeatureInsufficientDataError):
                continue

        if len(feature_rows) < self.settings.prediction_ml_min_samples:
            return None

        if not ml_model.fit(feature_rows, labels):
            return None

        target_row = self._build_combined_flat(target_features, target_context, target_xg)
        return ml_model.predict_proba(target_row)

    @staticmethod
    def _build_combined_flat(
        features: MatchFeatures,
        context: MatchContext,
        xg: MatchXG | None,
    ) -> dict[str, float | int | bool]:
        combined: dict[str, float | int | bool] = {}
        combined.update(features.flat_features())
        combined.update(context.flat_features())
        if xg is not None:
            combined.update(xg.flat_features())
        return combined

    @staticmethod
    def _build_features_snapshot(
        features: MatchFeatures,
        context: MatchContext,
        xg: MatchXG | None,
    ) -> dict:
        snapshot = {
            "features": features.to_dict(),
            "context": context.to_dict(),
        }
        if xg is not None:
            snapshot["xg"] = xg.to_dict()
        return snapshot

    @staticmethod
    def _get_1x2_probs(markets: list[MarketProbabilities]) -> dict[str, float]:
        for market in markets:
            if market.market_code == MARKET_1X2:
                return market.probabilities
        return {}

    @staticmethod
    def _replace_1x2_market(
        markets: list[MarketProbabilities],
        blended: dict[str, float],
        model_type: str,
    ) -> list[MarketProbabilities]:
        updated: list[MarketProbabilities] = []
        for market in markets:
            if market.market_code == MARKET_1X2:
                updated.append(
                    MarketProbabilities(
                        market_code=MARKET_1X2,
                        probabilities=blended,
                        model_type=model_type,
                    )
                )
            else:
                updated.append(market)
        return updated
