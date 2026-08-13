"""Extraction des résultats réels et collecte historique."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.calibration.schemas import MarketEvaluationRecord
from app.models.match import Match
from app.prediction.constants import (
    MARKET_1X2,
    MARKET_BTTS,
    MARKET_OU25,
    SELECTION_AWAY,
    SELECTION_DRAW,
    SELECTION_HOME,
    SELECTION_NO,
    SELECTION_OVER,
    SELECTION_UNDER,
    SELECTION_YES,
)
from app.prediction.exceptions import InsufficientPredictionDataError, MatchNotFoundError
from app.prediction.prediction_engine import PredictionEngine
from app.prediction.schemas import MatchPrediction
from app.repositories.prediction_data_repository import PredictionDataRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)

MARKET_SELECTIONS = {
    MARKET_1X2: (SELECTION_HOME, SELECTION_DRAW, SELECTION_AWAY),
    MARKET_BTTS: (SELECTION_YES, SELECTION_NO),
    MARKET_OU25: (SELECTION_OVER, SELECTION_UNDER),
}


def actual_selection_for_market(match: Match, market_code: str) -> str | None:
    """Retourne l'issue réelle pour un marché."""
    if match.home_score is None or match.away_score is None:
        return None

    if market_code == MARKET_1X2:
        if match.home_score > match.away_score:
            return SELECTION_HOME
        if match.home_score == match.away_score:
            return SELECTION_DRAW
        return SELECTION_AWAY

    if market_code == MARKET_BTTS:
        if match.home_score > 0 and match.away_score > 0:
            return SELECTION_YES
        return SELECTION_NO

    if market_code == MARKET_OU25:
        total = match.home_score + match.away_score
        return SELECTION_OVER if total > 2 else SELECTION_UNDER

    return None


def records_from_prediction(
    prediction: MatchPrediction,
    match: Match,
) -> list[MarketEvaluationRecord]:
    """Convertit une prédiction + match terminé en records d'évaluation."""
    records: list[MarketEvaluationRecord] = []
    for market in prediction.markets:
        actual = actual_selection_for_market(match, market.market_code)
        if actual is None:
            continue
        records.append(
            MarketEvaluationRecord(
                match_id=match.id,
                market_code=market.market_code,
                probabilities=dict(market.probabilities),
                actual_selection=actual,
            )
        )
    return records


class PredictionEvaluator:
    """Collecte prédictions historiques pour calibration / évaluation."""

    def __init__(self, session: Session, prediction_engine: PredictionEngine):
        self.session = session
        self.prediction_engine = prediction_engine
        self.prediction_data = PredictionDataRepository(session)

    def collect_season_records(
        self,
        season_id: int,
        before_date: datetime,
        *,
        competition_id: int | None = None,
        limit: int | None = None,
    ) -> list[MarketEvaluationRecord]:
        """Génère des records en rejouant le Prediction Engine sur l'historique."""
        matches = self.prediction_data.get_season_finished_matches(
            season_id,
            before_date,
            competition_id=competition_id,
        )
        if limit is not None:
            matches = matches[:limit]

        records: list[MarketEvaluationRecord] = []
        skipped = 0
        for match in matches:
            try:
                prediction = self.prediction_engine.build_prediction(
                    match.id,
                    as_of=match.scheduled_at,
                )
                records.extend(records_from_prediction(prediction, match))
            except (MatchNotFoundError, InsufficientPredictionDataError) as exc:
                skipped += 1
                log_event(
                    logger,
                    "CALIBRATION_RECORD_SKIPPED",
                    level="WARNING",
                    match_id=match.id,
                    reason=str(exc),
                )

        log_event(
            logger,
            "CALIBRATION_RECORDS_COLLECTED",
            season_id=season_id,
            matches=len(matches),
            records=len(records),
            skipped=skipped,
        )
        return records
