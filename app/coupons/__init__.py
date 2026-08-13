"""Coupon Generator — SAFE / VALUE / HIGH_ODDS / FREE."""

__all__ = [
    "CouponGenerator",
    "CouponCandidate",
    "CouponGenerationResult",
    "GeneratedCoupon",
    "CouponGeneratorError",
]


def __getattr__(name: str):
    if name == "CouponGenerator":
        from app.coupons.coupon_generator import CouponGenerator
        return CouponGenerator
    if name in ("CouponCandidate", "CouponGenerationResult", "GeneratedCoupon"):
        from app.coupons.schemas import CouponCandidate, CouponGenerationResult, GeneratedCoupon
        mapping = {
            "CouponCandidate": CouponCandidate,
            "CouponGenerationResult": CouponGenerationResult,
            "GeneratedCoupon": GeneratedCoupon,
        }
        return mapping[name]
    if name == "CouponGeneratorError":
        from app.coupons.exceptions import CouponGeneratorError
        return CouponGeneratorError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
