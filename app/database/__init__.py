"""Couche d'accès PostgreSQL."""

from app.database.base import Base, TimestampMixin
from app.database.enums import (
    ConfidenceLevel,
    CouponStatus,
    CouponType,
    DataStatus,
    InfoReliability,
    MatchStatus,
    PaymentMethod,
    PaymentStatus,
    RiskDecision,
    SubscriptionStatus,
    SystemRunStatus,
)
from app.database.session import (
    check_database_connection,
    create_engine_from_url,
    get_db,
    get_engine,
    get_session_factory,
    reset_engine,
    session_scope,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "SubscriptionStatus",
    "PaymentStatus",
    "PaymentMethod",
    "MatchStatus",
    "DataStatus",
    "ConfidenceLevel",
    "RiskDecision",
    "CouponType",
    "CouponStatus",
    "SystemRunStatus",
    "InfoReliability",
    "get_engine",
    "get_session_factory",
    "get_db",
    "session_scope",
    "check_database_connection",
    "create_engine_from_url",
    "reset_engine",
]
