"""Value Engine — comparaison probabilité modèle vs marché."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calibration.schemas import CalibratedMatchPrediction
from app.config.settings import Settings, get_settings
from app.models.match import Match
from app.prediction.schemas import MatchPrediction
from app.repositories.odds_repository import OddsRepository
from app.utils.logging import get_logger, log_event
from app.value.exceptions import MatchNotFoundError, OddsNotFoundError
from app.value.implied import compute_edge, decimal_to_implied, normalize_overround
from app.value.schemas import MatchValueAnalysis, ValueOpportunity

logger = get_logger(__name__)


class ValueEngine:
    """
    Compare les probabilités du modèle aux cotes bookmakers.

    Architecture :
    MODÈLE → PROBABILITÉ → COTES → VALUE EDGE
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.odds_repo = OddsRepository(session)

    def analyze(
        self,
        prediction: MatchPrediction | CalibratedMatchPrediction,
        *,
        bookmaker: str | None = None,
    ) -> MatchValueAnalysis:
        """Analyse value pour une prédiction et les cotes en base."""
        match_id = prediction.match_id
        match = self.session.scalar(select(Match).where(Match.id == match_id))
        if match is None:
            raise MatchNotFoundError(f"Match {match_id} introuvable")

        preferred = bookmaker or self.settings.odds_preferred_bookmaker or None
        odds_snapshot = self.odds_repo.get_market_odds_snapshot(match_id, bookmaker=preferred)

        if not odds_snapshot and preferred:
            odds_snapshot = self.odds_repo.get_market_odds_snapshot(match_id)

        if not odds_snapshot:
            raise OddsNotFoundError(f"Aucune cote pour match {match_id}")

        model_markets = self._get_model_markets(prediction)
        opportunities: list[ValueOpportunity] = []
        threshold = self.settings.value_edge_min_threshold

        for market_code, selections in odds_snapshot.items():
            model_probs = model_markets.get(market_code)
            if not model_probs:
                continue

            raw_implied = {
                sel: decimal_to_implied(float(row.odds))
                for sel, row in selections.items()
            }
            normalized = (
                normalize_overround(raw_implied)
                if self.settings.value_use_normalized_implied
                else raw_implied
            )

            for selection, odd_row in selections.items():
                model_prob = model_probs.get(selection)
                if model_prob is None:
                    continue

                implied_raw = raw_implied[selection]
                implied = normalized[selection]
                edge = compute_edge(model_prob, implied)

                opportunities.append(
                    ValueOpportunity(
                        match_id=match_id,
                        market_code=market_code,
                        selection=selection,
                        model_probability=model_prob,
                        implied_probability_raw=implied_raw,
                        implied_probability=implied,
                        decimal_odds=float(odd_row.odds),
                        value_edge=edge,
                        bookmaker=odd_row.bookmaker,
                        is_value=edge >= threshold,
                        overround_normalized=self.settings.value_use_normalized_implied,
                    )
                )

        analysis = MatchValueAnalysis(
            match_id=match_id,
            opportunities=opportunities,
            metadata={
                "threshold": threshold,
                "bookmaker_filter": preferred,
                "markets_analyzed": list(odds_snapshot.keys()),
            },
        )

        log_event(
            logger,
            "VALUE_ANALYZED",
            match_id=match_id,
            opportunities=len(opportunities),
            has_value=analysis.has_value,
        )
        return analysis

    @staticmethod
    def _get_model_markets(
        prediction: MatchPrediction | CalibratedMatchPrediction,
    ) -> dict[str, dict[str, float]]:
        if isinstance(prediction, CalibratedMatchPrediction):
            markets = prediction.markets
        else:
            markets = prediction.markets
        return {m.market_code: dict(m.probabilities) for m in markets}
