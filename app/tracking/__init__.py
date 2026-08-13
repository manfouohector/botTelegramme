"""Tracking Engine — settlement + historique + métriques."""

__all__ = [
    "TrackingEngine",
    "SettlementResult",
    "CouponSettlementResult",
    "TrackingMetrics",
    "HistoryEntry",
    "TrackingError",
]


def __getattr__(name: str):
    if name == "TrackingEngine":
        from app.tracking.tracking_engine import TrackingEngine
        return TrackingEngine
    if name in (
        "SettlementResult",
        "CouponSettlementResult",
        "TrackingMetrics",
        "HistoryEntry",
    ):
        from app.tracking.schemas import (
            CouponSettlementResult,
            HistoryEntry,
            SettlementResult,
            TrackingMetrics,
        )
        mapping = {
            "SettlementResult": SettlementResult,
            "CouponSettlementResult": CouponSettlementResult,
            "TrackingMetrics": TrackingMetrics,
            "HistoryEntry": HistoryEntry,
        }
        return mapping[name]
    if name == "TrackingError":
        from app.tracking.exceptions import TrackingError
        return TrackingError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
