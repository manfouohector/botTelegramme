"""Exceptions Coupon Generator."""


class CouponGeneratorError(Exception):
    """Erreur générique Coupon Generator."""


class InsufficientCandidatesError(CouponGeneratorError):
    """Pas assez de sélections qualifiées."""
