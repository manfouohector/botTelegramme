"""Persistance des prédictions."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.enums import ConfidenceLevel
from app.models.market import Market
from app.models.prediction import AIModel, Prediction
from app.prediction.constants import ENGINE_VERSION
from app.prediction.schemas import MatchPrediction


class PredictionRepository:
    """Sauvegarde prédictions et accès marchés / modèles."""

    def __init__(self, session: Session):
        self.session = session

    def get_or_create_market(self, code: str, name: str | None = None) -> Market:
        market = self.session.scalar(select(Market).where(Market.code == code))
        if market is None:
            market = Market(code=code, name=name or code, active=True)
            self.session.add(market)
            self.session.flush()
        return market

    def get_or_create_model(self, name: str, model_type: str, version: str = ENGINE_VERSION) -> AIModel:
        model = self.session.scalar(
            select(AIModel).where(AIModel.name == name, AIModel.version == version)
        )
        if model is None:
            model = AIModel(name=name, version=version, type=model_type, active=True)
            self.session.add(model)
            self.session.flush()
        return model

    def save_prediction(self, prediction: MatchPrediction) -> list[Prediction]:
        """Persiste chaque issue de marché comme ligne Prediction."""
        ai_model = self.get_or_create_model(
            name=prediction.model_type,
            model_type=prediction.model_type,
            version=prediction.model_version,
        )
        rows: list[Prediction] = []
        for market_pred in prediction.markets:
            market = self.get_or_create_market(
                market_pred.market_code,
                name=market_pred.market_code,
            )
            for selection, probability in market_pred.probabilities.items():
                row = Prediction(
                    match_id=prediction.match_id,
                    market_id=market.id,
                    model_id=ai_model.id,
                    model_version=prediction.model_version,
                    selection=selection,
                    probability=Decimal(str(round(probability, 6))),
                    confidence=prediction.confidence,
                    features_snapshot={
                        **prediction.features_snapshot,
                        "market_model_type": market_pred.model_type,
                    },
                )
                self.session.add(row)
                rows.append(row)
        self.session.flush()
        return rows

    def get_predictions_for_match(self, match_id: int) -> list[Prediction]:
        return list(
            self.session.scalars(
                select(Prediction).where(Prediction.match_id == match_id)
            ).all()
        )
