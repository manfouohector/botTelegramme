"""Énumérations partagées pour la base de données."""

from enum import StrEnum


class SubscriptionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"


class PaymentMethod(StrEnum):
    MANUEL_WHATSAPP = "manuel_whatsapp"
    MOBILE_MONEY = "mobile_money"


class MatchStatus(StrEnum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class DataStatus(StrEnum):
    FRESH = "FRESH"
    STALE = "STALE"
    MISSING = "MISSING"
    INCOMPLETE = "INCOMPLETE"
    ERROR = "ERROR"


class ConfidenceLevel(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RiskDecision(StrEnum):
    APPROVE = "APPROVE"
    WARNING = "WARNING"
    REJECT = "REJECT"


class CouponType(StrEnum):
    FREE = "FREE"
    SAFE = "SAFE"
    VALUE = "VALUE"
    HIGH_ODDS = "HIGH_ODDS"


class CouponStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CONFIRMED = "CONFIRMED"
    SETTLED = "SETTLED"
    CANCELLED = "CANCELLED"


class SystemRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class InfoReliability(StrEnum):
    OFFICIAL = "OFFICIAL"
    PROBABLE = "PROBABLE"
    RUMOR = "RUMOR"
