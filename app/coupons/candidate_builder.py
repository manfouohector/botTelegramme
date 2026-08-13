"""Construction de candidats depuis le pipeline."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.coupons.schemas import CouponCandidate
from app.prediction.schemas import MatchPrediction
from app.risk.schemas import MatchRiskAssessment, SelectionRiskResult
from app.value.schemas import MatchValueAnalysis, ValueOpportunity


def build_candidate(
    prediction: MatchPrediction,
    opportunity: ValueOpportunity,
    risk: MatchRiskAssessment | SelectionRiskResult,
    *,
    home_team: str = "",
    away_team: str = "",
    scheduled_at: str = "",
) -> CouponCandidate | None:
    """Construit un candidat si publishable."""
    if isinstance(risk, MatchRiskAssessment):
        selection_risk = next(
            (
                s
                for s in risk.selections
                if s.market_code == opportunity.market_code
                and s.selection == opportunity.selection
            ),
            None,
        )
        if selection_risk is None or not selection_risk.publishable:
            return None
        risk = selection_risk

    if not risk.publishable:
        return None

    return CouponCandidate(
        match_id=prediction.match_id,
        external_match_id=prediction.external_match_id,
        market_code=opportunity.market_code,
        selection=opportunity.selection,
        probability=opportunity.model_probability,
        decimal_odds=opportunity.decimal_odds,
        confidence=risk.confidence,
        risk_decision=risk.decision,
        value_edge=opportunity.value_edge,
        is_value=opportunity.is_value,
        home_team=home_team,
        away_team=away_team,
        scheduled_at=scheduled_at,
    )


def build_candidates_from_analyses(
    session: Session,
    items: list[tuple[MatchPrediction, MatchValueAnalysis, MatchRiskAssessment]],
) -> list[CouponCandidate]:
    """Construit tous les candidats publishable depuis une liste d'analyses."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.match import Match

    candidates: list[CouponCandidate] = []
    for prediction, value_analysis, risk in items:
        if not risk.publishable:
            continue
        opportunity = value_analysis.best_value
        if opportunity is None:
            continue

        match = session.scalar(
            select(Match)
            .options(selectinload(Match.home_team), selectinload(Match.away_team))
            .where(Match.id == prediction.match_id)
        )
        home = match.home_team.name if match and match.home_team else ""
        away = match.away_team.name if match and match.away_team else ""
        scheduled = match.scheduled_at.isoformat() if match else ""

        candidate = build_candidate(
            prediction,
            opportunity,
            risk,
            home_team=home,
            away_team=away,
            scheduled_at=scheduled,
        )
        if candidate:
            candidates.append(candidate)

    return candidates
