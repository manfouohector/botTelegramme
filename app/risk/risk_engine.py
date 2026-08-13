"""Risk Engine — validation avant publication."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calibration.schemas import CalibratedMatchPrediction
from app.config.settings import Settings, get_settings
from app.database.enums import RiskDecision
from app.models.match import Match
from app.prediction.schemas import MatchPrediction
from app.repositories.risk_repository import RiskRepository
from app.utils.logging import get_logger, log_event
from app.risk.exceptions import MatchNotFoundError
from app.risk.rules import (
    aggregate_decision,
    evaluate_match_factors,
    evaluate_selection_factors,
    is_publishable,
)
from app.risk.schemas import MatchRiskAssessment, RiskFactorItem, SelectionRiskResult
from app.value.schemas import MatchValueAnalysis, ValueOpportunity

logger = get_logger(__name__)


class RiskEngine:
    """
    Filtre les prédictions avant publication (Coupon Generator).

    Décisions : APPROVE | WARNING | REJECT
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.risk_repo = RiskRepository(session)

    def assess(
        self,
        prediction: MatchPrediction | CalibratedMatchPrediction,
        value_analysis: MatchValueAnalysis | None = None,
        *,
        opportunity: ValueOpportunity | None = None,
        persist: bool = False,
    ) -> MatchRiskAssessment:
        """Évalue le risque global + sélection principale si value."""
        match = self.session.scalar(select(Match).where(Match.id == prediction.match_id))
        if match is None:
            raise MatchNotFoundError(f"Match {prediction.match_id} introuvable")

        confidence = prediction.confidence
        match_factors = evaluate_match_factors(
            self.session, match, prediction, settings=self.settings
        )

        target_opportunity = opportunity
        if target_opportunity is None and value_analysis is not None:
            target_opportunity = value_analysis.best_value

        selection_factors: list[RiskFactorItem] = []
        selections: list[SelectionRiskResult] = []

        if target_opportunity is not None:
            selection_factors = evaluate_selection_factors(
                target_opportunity, value_analysis, settings=self.settings
            )
            all_factors = _dedupe_factors(match_factors + selection_factors)
            decision = aggregate_decision(all_factors, confidence, self.settings)
            selections.append(
                SelectionRiskResult(
                    match_id=prediction.match_id,
                    market_code=target_opportunity.market_code,
                    selection=target_opportunity.selection,
                    decision=decision,
                    confidence=confidence,
                    factors=all_factors,
                    publishable=is_publishable(decision),
                )
            )
        elif value_analysis is not None:
            selection_factors = evaluate_selection_factors(
                None, value_analysis, settings=self.settings
            )
        else:
            selection_factors = evaluate_selection_factors(
                None, None, settings=self.settings
            )

        all_factors = _dedupe_factors(match_factors + selection_factors)
        decision = aggregate_decision(all_factors, confidence, self.settings)

        assessment = MatchRiskAssessment(
            match_id=prediction.match_id,
            decision=decision,
            confidence=confidence,
            factors=all_factors,
            selections=selections,
            publishable=is_publishable(decision),
            metadata={
                "factor_count": len(all_factors),
                "has_value_opportunity": target_opportunity is not None,
            },
        )

        log_event(
            logger,
            "RISK_ASSESSED",
            match_id=prediction.match_id,
            decision=decision.value,
            publishable=assessment.publishable,
            factors=len(all_factors),
        )

        if persist:
            self.risk_repo.save_factors(prediction.match_id, all_factors)

        return assessment


def _dedupe_factors(factors: list[RiskFactorItem]) -> list[RiskFactorItem]:
    seen: set[str] = set()
    result: list[RiskFactorItem] = []
    for factor in factors:
        if factor.factor in seen:
            continue
        seen.add(factor.factor)
        result.append(factor)
    return result
