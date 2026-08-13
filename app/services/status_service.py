"""Service statut génération du jour (/status)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.database.enums import CouponType, SystemRunStatus
from app.generation.constants import GENERATION_RUN_TYPE
from app.generation.schemas import CouponTypeStatus, DailyStatus, decode_run_metadata, parse_failed_stage
from app.repositories.generation_repository import GenerationRepository


class StatusService:
    """Construit le statut journalier à partir de system_runs et coupons."""

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.repo = GenerationRepository(session)

    def get_daily_status(self, target_date: date | None = None) -> DailyStatus:
        day = target_date or self._today()
        status = DailyStatus(target_date=day)

        run = self.repo.get_generation_run_for_date(
            GENERATION_RUN_TYPE,
            day,
            self.settings.timezone,
        )
        skip_reasons: dict[str, str] = {}
        if run is not None:
            status.system_run_id = run.id
            status.run_status = run.status
            status.matches_analyzed = run.matches_processed
            status.predictions_created = run.predictions_created
            status.matches_fetched = run.matches_processed

            if run.status == SystemRunStatus.FAILED:
                status.generation_error = True
                module, detail = parse_failed_stage(run.error_message)
                status.failed_module = module
                status.error_detail = detail
            skip_reasons = decode_run_metadata(run.error_message)

        match_count = self.repo.count_matches_for_date(day, self.settings.timezone)
        if match_count == 0 and run is None:
            status.no_matches_today = True
            return status

        if run is None and match_count > 0:
            status.matches_fetched = match_count
            status.matches_analyzed = 0

        status.published = self.repo.any_coupon_published_for_date(day, self.settings.timezone)
        status.coupons = self._build_coupon_statuses(day, skip_reasons)
        return status

    def _build_coupon_statuses(
        self,
        day: date,
        skip_reasons: dict[str, str],
    ) -> list[CouponTypeStatus]:
        items: list[CouponTypeStatus] = []
        for coupon_type in GenerationRepository.COUPON_TYPES:
            coupon = self.repo.get_latest_coupon_by_type(
                coupon_type, day, self.settings.timezone
            )
            if coupon is not None:
                selections = len(coupon.predictions)
                sent = coupon.status in GenerationRepository.PUBLISHED_STATUSES
                items.append(
                    CouponTypeStatus(
                        coupon_type=coupon_type,
                        created=True,
                        sent=sent,
                        coupon_id=coupon.id,
                        selections_count=selections,
                    )
                )
            else:
                reason = skip_reasons.get(coupon_type.value)
                if not reason:
                    reason = self._default_skip_reason(coupon_type)
                items.append(
                    CouponTypeStatus(
                        coupon_type=coupon_type,
                        created=False,
                        sent=False,
                        skip_reason=reason,
                    )
                )
        return items

    @staticmethod
    def _default_skip_reason(coupon_type: CouponType) -> str:
        if coupon_type == CouponType.HIGH_ODDS:
            return "aucune sélection n'a passé le Risk Engine."
        return "critères de sélection non atteints."

    def _today(self) -> date:
        tz = ZoneInfo(self.settings.timezone)
        return datetime.now(tz).date()
