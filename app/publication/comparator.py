"""Comparaison de coupons pour éviter les doublons."""

from __future__ import annotations

from app.coupons.schemas import GeneratedCoupon
from app.models.coupon import Coupon


def selection_fingerprint_from_coupon(coupon: Coupon) -> tuple[tuple[int, str, str], ...]:
    links = sorted(coupon.predictions, key=lambda link: link.position)
    fingerprint: list[tuple[int, str, str]] = []
    for link in links:
        pred = link.prediction
        if pred is None or pred.market is None:
            continue
        fingerprint.append((pred.match_id, pred.market.code, pred.selection))
    return tuple(fingerprint)


def selection_fingerprint_from_generated(generated: GeneratedCoupon) -> tuple[tuple[int, str, str], ...]:
    return tuple(
        (c.match_id, c.market_code, c.selection)
        for c in generated.candidates
    )


def coupons_unchanged(
    current: tuple[tuple[int, str, str], ...],
    previous: tuple[tuple[int, str, str], ...],
) -> bool:
    return bool(current) and current == previous
