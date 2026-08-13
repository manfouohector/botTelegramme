"""Service historique coupons (/history)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.generation.schemas import CouponTypeHistory, HistoryDaySummary
from app.repositories.generation_repository import GenerationRepository


class HistoryService:
    """Résumé des sélections réglées par type de coupon."""

    TYPE_ORDER = GenerationRepository.COUPON_TYPES

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.repo = GenerationRepository(session)

    def get_history(self, target_date: date | None = None) -> HistoryDaySummary:
        day = target_date or self.repo.find_latest_settled_match_day(self.settings.timezone)
        if day is None:
            return HistoryDaySummary(target_date=date.today())

        stats = self.repo.get_settled_selection_stats_for_date(day, self.settings.timezone)
        summary = HistoryDaySummary(target_date=day)

        total_won = 0
        total_lost = 0
        for coupon_type in self.TYPE_ORDER:
            won, total = stats.get(coupon_type, (0, 0))
            if total > 0:
                summary.by_type.append(
                    CouponTypeHistory(
                        coupon_type=coupon_type,
                        selections_won=won,
                        selections_total=total,
                    )
                )
                total_won += won
                total_lost += total - won

        summary.total_won = total_won
        summary.total_lost = total_lost
        return summary

    @staticmethod
    def parse_date_arg(raw: str | None) -> date | None:
        if not raw:
            return None
        try:
            return date.fromisoformat(raw.strip())
        except ValueError:
            return None

    def _today(self) -> date:
        tz = ZoneInfo(self.settings.timezone)
        return datetime.now(tz).date()
