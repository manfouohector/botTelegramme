"""Schémas génération, statut et historique admin."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime

from app.coupons.schemas import CouponGenerationResult
from app.database.enums import CouponType, SystemRunStatus
from app.generation.constants import GEN_META_PREFIX


@dataclass
class GenerationBatchResult:
    """Résultat complet d'une exécution /generate."""

    target_date: date
    matches_fetched: int = 0
    matches_analyzed: int = 0
    predictions_created: int = 0
    coupons_created: int = 0
    coupon_result: CouponGenerationResult | None = None
    published: bool = False
    publication_deferred: bool = False
    publication_result: object | None = None
    failed_stage: str | None = None
    error_message: str | None = None
    skip_reasons: dict[str, str] = field(default_factory=dict)
    system_run_id: int | None = None
    status: SystemRunStatus = SystemRunStatus.SUCCESS

    def to_dict(self) -> dict:
        return {
            "target_date": self.target_date.isoformat(),
            "matches_fetched": self.matches_fetched,
            "matches_analyzed": self.matches_analyzed,
            "predictions_created": self.predictions_created,
            "coupons_created": self.coupons_created,
            "coupon_result": self.coupon_result.to_dict() if self.coupon_result else None,
            "published": self.published,
            "publication_deferred": self.publication_deferred,
            "publication_result": (
                self.publication_result.to_dict()
                if self.publication_result is not None and hasattr(self.publication_result, "to_dict")
                else None
            ),
            "failed_stage": self.failed_stage,
            "error_message": self.error_message,
            "skip_reasons": self.skip_reasons,
            "system_run_id": self.system_run_id,
            "status": self.status.value,
        }


@dataclass
class CouponTypeStatus:
    """État d'un type de coupon pour /status."""

    coupon_type: CouponType
    created: bool
    sent: bool
    skip_reason: str | None = None
    coupon_id: int | None = None
    selections_count: int = 0

    def to_dict(self) -> dict:
        return {
            "coupon_type": self.coupon_type.value,
            "created": self.created,
            "sent": self.sent,
            "skip_reason": self.skip_reason,
            "coupon_id": self.coupon_id,
            "selections_count": self.selections_count,
        }


@dataclass
class DailyStatus:
    """Statut génération du jour pour /status."""

    target_date: date
    matches_fetched: int = 0
    matches_analyzed: int = 0
    predictions_created: int = 0
    coupons: list[CouponTypeStatus] = field(default_factory=list)
    generation_error: bool = False
    failed_module: str | None = None
    error_detail: str | None = None
    published: bool = False
    no_matches_today: bool = False
    system_run_id: int | None = None
    run_status: SystemRunStatus | None = None

    def to_dict(self) -> dict:
        return {
            "target_date": self.target_date.isoformat(),
            "matches_fetched": self.matches_fetched,
            "matches_analyzed": self.matches_analyzed,
            "predictions_created": self.predictions_created,
            "coupons": [c.to_dict() for c in self.coupons],
            "generation_error": self.generation_error,
            "failed_module": self.failed_module,
            "error_detail": self.error_detail,
            "published": self.published,
            "no_matches_today": self.no_matches_today,
            "system_run_id": self.system_run_id,
            "run_status": self.run_status.value if self.run_status else None,
        }


@dataclass
class CouponTypeHistory:
    """Résumé historique par type de coupon."""

    coupon_type: CouponType
    selections_won: int
    selections_total: int

    @property
    def display_ratio(self) -> str:
        return f"{self.selections_won}/{self.selections_total}"


@dataclass
class HistoryDaySummary:
    """Historique d'une journée pour /history."""

    target_date: date
    by_type: list[CouponTypeHistory] = field(default_factory=list)
    total_won: int = 0
    total_lost: int = 0

    @property
    def has_data(self) -> bool:
        return any(h.selections_total > 0 for h in self.by_type)

    def to_dict(self) -> dict:
        return {
            "target_date": self.target_date.isoformat(),
            "by_type": [
                {
                    "coupon_type": h.coupon_type.value,
                    "selections_won": h.selections_won,
                    "selections_total": h.selections_total,
                }
                for h in self.by_type
            ],
            "total_won": self.total_won,
            "total_lost": self.total_lost,
        }


def encode_run_metadata(*, skip_reasons: dict[str, str]) -> str | None:
    if not skip_reasons:
        return None
    payload = json.dumps({"skip_reasons": skip_reasons}, ensure_ascii=False)
    return f"{GEN_META_PREFIX}{payload}"


def decode_run_metadata(error_message: str | None) -> dict[str, str]:
    if not error_message or not error_message.startswith(GEN_META_PREFIX):
        return {}
    try:
        payload = json.loads(error_message[len(GEN_META_PREFIX) :])
    except json.JSONDecodeError:
        return {}
    reasons = payload.get("skip_reasons", {})
    if isinstance(reasons, dict):
        return {str(k): str(v) for k, v in reasons.items()}
    return {}


def parse_failed_stage(error_message: str | None) -> tuple[str | None, str | None]:
    """Extrait module et détail depuis 'Stage: message'."""
    if not error_message or error_message.startswith(GEN_META_PREFIX):
        return None, None
    if ":" not in error_message:
        return None, error_message
    module, detail = error_message.split(":", 1)
    return module.strip(), detail.strip()
