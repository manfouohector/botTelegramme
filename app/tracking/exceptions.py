"""Exceptions Tracking Engine."""


class TrackingError(Exception):
    """Erreur générique Tracking."""


class MatchNotSettleableError(TrackingError):
    """Match sans score ou statut incompatible."""


class PredictionAlreadySettledError(TrackingError):
    """Prédiction déjà réglée."""


class CouponNotSettleableError(TrackingError):
    """Coupon non éligible au settlement."""
