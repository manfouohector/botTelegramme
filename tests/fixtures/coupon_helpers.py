"""Helpers pour tests Coupon Generator."""

from app.coupons.schemas import CouponCandidate
from app.database.enums import ConfidenceLevel, RiskDecision


def make_candidate(
    match_id: int,
    *,
    external_match_id: int | None = None,
    market_code: str = "1X2",
    selection: str = "HOME",
    probability: float = 0.60,
    decimal_odds: float = 1.80,
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    risk_decision: RiskDecision = RiskDecision.APPROVE,
    value_edge: float | None = None,
    is_value: bool = False,
    home_team: str = "Home",
    away_team: str = "Away",
) -> CouponCandidate:
    """Fabrique un candidat publishable pour les tests."""
    return CouponCandidate(
        match_id=match_id,
        external_match_id=external_match_id or match_id * 1000,
        market_code=market_code,
        selection=selection,
        probability=probability,
        decimal_odds=decimal_odds,
        confidence=confidence,
        risk_decision=risk_decision,
        value_edge=value_edge,
        is_value=is_value,
        home_team=home_team,
        away_team=away_team,
    )


def make_safe_pool(count: int, *, start_id: int = 1) -> list[CouponCandidate]:
    """Pool de candidats éligibles SAFE."""
    return [
        make_candidate(
            start_id + i,
            probability=0.58 + i * 0.02,
            decimal_odds=1.5 + i * 0.1,
            confidence=ConfidenceLevel.HIGH,
            risk_decision=RiskDecision.APPROVE,
        )
        for i in range(count)
    ]


def make_value_pool(count: int, *, start_id: int = 101) -> list[CouponCandidate]:
    """Pool de candidats éligibles VALUE."""
    return [
        make_candidate(
            start_id + i,
            probability=0.55 + i * 0.01,
            decimal_odds=2.0 + i * 0.2,
            is_value=True,
            value_edge=0.06 + i * 0.01,
        )
        for i in range(count)
    ]


def make_high_odds_pool(count: int, *, start_id: int = 201) -> list[CouponCandidate]:
    """Pool de candidats éligibles HIGH_ODDS (cote combinée >= 15)."""
    odds = [4.0, 3.5, 3.0, 2.8, 2.6, 2.5, 2.5][:count]
    return [
        make_candidate(
            start_id + i,
            probability=0.30 + i * 0.02,
            decimal_odds=odds[i] if i < len(odds) else 3.0,
        )
        for i in range(count)
    ]
