"""Schémas Coupon Generator."""

from dataclasses import dataclass, field

from app.database.enums import ConfidenceLevel, CouponType, RiskDecision


@dataclass
class CouponCandidate:
    """Sélection éligible après Risk Engine."""

    match_id: int
    external_match_id: int
    market_code: str
    selection: str
    probability: float
    decimal_odds: float
    confidence: ConfidenceLevel
    risk_decision: RiskDecision
    value_edge: float | None = None
    is_value: bool = False
    home_team: str = ""
    away_team: str = ""
    scheduled_at: str = ""

    @property
    def publishable(self) -> bool:
        return self.risk_decision in (RiskDecision.APPROVE, RiskDecision.WARNING)

    @property
    def candidate_key(self) -> tuple[int, str, str]:
        return (self.match_id, self.market_code, self.selection)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "external_match_id": self.external_match_id,
            "market_code": self.market_code,
            "selection": self.selection,
            "probability": round(self.probability, 6),
            "decimal_odds": round(self.decimal_odds, 4),
            "confidence": self.confidence.value,
            "risk_decision": self.risk_decision.value,
            "value_edge": round(self.value_edge, 6) if self.value_edge is not None else None,
            "is_value": self.is_value,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "scheduled_at": self.scheduled_at,
        }


@dataclass
class GeneratedCoupon:
    """Coupon généré (pas encore persisté ou persisté)."""

    coupon_type: CouponType
    candidates: list[CouponCandidate]
    total_odds: float
    coupon_id: int | None = None
    skipped: bool = False
    skip_reason: str | None = None

    def to_dict(self) -> dict:
        return {
            "coupon_type": self.coupon_type.value,
            "selections_count": len(self.candidates),
            "total_odds": round(self.total_odds, 4),
            "coupon_id": self.coupon_id,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "candidates": [c.to_dict() for c in self.candidates],
        }


@dataclass
class CouponGenerationResult:
    """Résultat complet d'une génération journalière."""

    free: GeneratedCoupon | None = None
    safe: GeneratedCoupon | None = None
    value: GeneratedCoupon | None = None
    high_odds: GeneratedCoupon | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def coupons_created(self) -> int:
        return sum(
            1 for c in (self.free, self.safe, self.value, self.high_odds)
            if c is not None and not c.skipped and len(c.candidates) > 0
        )

    def all_coupons(self) -> list[GeneratedCoupon]:
        return [
            c for c in (self.free, self.safe, self.value, self.high_odds)
            if c is not None and not c.skipped and c.candidates
        ]

    def to_dict(self) -> dict:
        return {
            "coupons_created": self.coupons_created,
            "free": self.free.to_dict() if self.free else None,
            "safe": self.safe.to_dict() if self.safe else None,
            "value": self.value.to_dict() if self.value else None,
            "high_odds": self.high_odds.to_dict() if self.high_odds else None,
            "metadata": self.metadata,
        }
