"""Sélection des candidats par type de coupon."""

from __future__ import annotations

from app.config.settings import Settings
from app.coupons.schemas import CouponCandidate, GeneratedCoupon
from app.database.enums import ConfidenceLevel, CouponType, RiskDecision


def combined_odds(candidates: list[CouponCandidate]) -> float:
    total = 1.0
    for c in candidates:
        total *= c.decimal_odds
    return total


def select_safe(candidates: list[CouponCandidate], settings: Settings) -> GeneratedCoupon:
    """Sélections à faible risque relatif — confiance élevée, cotes modérées."""
    pool = [
        c for c in candidates
        if c.publishable
        and c.confidence == ConfidenceLevel.HIGH
        and c.risk_decision == RiskDecision.APPROVE
        and c.probability >= settings.coupon_safe_min_probability
        and c.decimal_odds <= settings.coupon_safe_max_odds
    ]
    pool.sort(key=lambda c: (-c.probability, -c.decimal_odds))
    selected = _dedupe_matches(pool)[: settings.coupon_safe_max_selections]

    if len(selected) < settings.coupon_safe_min_selections:
        return GeneratedCoupon(
            coupon_type=CouponType.SAFE,
            candidates=[],
            total_odds=0.0,
            skipped=True,
            skip_reason=f"Sélections SAFE insuffisantes ({len(selected)}/{settings.coupon_safe_min_selections})",
        )

    return GeneratedCoupon(
        coupon_type=CouponType.SAFE,
        candidates=selected,
        total_odds=combined_odds(selected),
    )


def select_value(candidates: list[CouponCandidate], settings: Settings) -> GeneratedCoupon:
    """Sélections avec edge value intéressant."""
    allowed_decisions = {RiskDecision.APPROVE}
    if settings.coupon_allow_warning_in_value:
        allowed_decisions.add(RiskDecision.WARNING)

    pool = [
        c for c in candidates
        if c.publishable
        and c.is_value
        and c.risk_decision in allowed_decisions
        and c.value_edge is not None
        and c.value_edge >= settings.value_edge_min_threshold
    ]
    pool.sort(key=lambda c: (-(c.value_edge or 0), -c.probability))
    selected = _dedupe_matches(pool)[: settings.coupon_value_max_selections]

    if len(selected) < settings.coupon_value_min_selections:
        return GeneratedCoupon(
            coupon_type=CouponType.VALUE,
            candidates=[],
            total_odds=0.0,
            skipped=True,
            skip_reason=f"Sélections VALUE insuffisantes ({len(selected)}/{settings.coupon_value_min_selections})",
        )

    return GeneratedCoupon(
        coupon_type=CouponType.VALUE,
        candidates=selected,
        total_odds=combined_odds(selected),
    )


def select_high_odds(candidates: list[CouponCandidate], settings: Settings) -> GeneratedCoupon:
    """Coupon cote combinée élevée — risque plus important."""
    pool = [
        c for c in candidates
        if c.publishable
        and c.decimal_odds >= settings.coupon_high_odds_min_odds
        and c.probability >= settings.coupon_high_odds_min_probability
    ]
    pool.sort(key=lambda c: (-c.decimal_odds, -c.probability))
    selected = _dedupe_matches(pool)[: settings.coupon_high_odds_max_selections]

    if len(selected) < settings.coupon_high_odds_min_selections:
        return GeneratedCoupon(
            coupon_type=CouponType.HIGH_ODDS,
            candidates=[],
            total_odds=0.0,
            skipped=True,
            skip_reason=(
                f"Sélections HIGH_ODDS insuffisantes ({len(selected)}/"
                f"{settings.coupon_high_odds_min_selections})"
            ),
        )

    total = combined_odds(selected)
    if total < settings.coupon_high_odds_min_combined:
        return GeneratedCoupon(
            coupon_type=CouponType.HIGH_ODDS,
            candidates=[],
            total_odds=total,
            skipped=True,
            skip_reason=f"Cote combinée trop faible ({total:.2f} < {settings.coupon_high_odds_min_combined})",
        )

    return GeneratedCoupon(
        coupon_type=CouponType.HIGH_ODDS,
        candidates=selected,
        total_odds=total,
    )


def select_free(
    candidates: list[CouponCandidate],
    settings: Settings,
    *,
    exclude_keys: set[tuple[int, str, str]] | None = None,
) -> GeneratedCoupon:
    """Coupon gratuit vitrine — bonne confiance, pas forcément value."""
    exclude = exclude_keys or set()
    pool = [
        c for c in candidates
        if c.publishable
        and c.candidate_key not in exclude
        and c.confidence in (ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM)
        and c.risk_decision == RiskDecision.APPROVE
        and c.probability >= settings.coupon_free_min_probability
    ]
    pool.sort(key=lambda c: (-c.probability, -(c.value_edge or 0)))
    selected = _dedupe_matches(pool)[: settings.coupon_free_max_selections]

    if len(selected) < settings.coupon_free_min_selections:
        return GeneratedCoupon(
            coupon_type=CouponType.FREE,
            candidates=[],
            total_odds=0.0,
            skipped=True,
            skip_reason=f"Sélections FREE insuffisantes ({len(selected)}/{settings.coupon_free_min_selections})",
        )

    return GeneratedCoupon(
        coupon_type=CouponType.FREE,
        candidates=selected,
        total_odds=combined_odds(selected),
    )


def _dedupe_matches(candidates: list[CouponCandidate]) -> list[CouponCandidate]:
    """Une seule sélection par match."""
    seen: set[int] = set()
    result: list[CouponCandidate] = []
    for c in candidates:
        if c.match_id in seen:
            continue
        seen.add(c.match_id)
        result.append(c)
    return result
