"""Service publication Telegram — canal Free + groupe Premium."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.backtesting.clv_service import ClvService
from app.config.settings import Settings, get_settings
from app.coupons.schemas import CouponGenerationResult
from app.database.enums import CouponType, SystemRunStatus
from app.publication.comparator import (
    coupons_unchanged,
    selection_fingerprint_from_coupon,
    selection_fingerprint_from_generated,
)
from app.publication.constants import PUBLICATION_RUN_TYPE
from app.publication.formatters import _resolve_coupon_type, format_confirmation_message, format_coupon_message
from app.publication.schemas import PublicationBatchResult, PublishedCouponResult
from app.repositories.coupon_repository import CouponRepository
from app.repositories.system_run_repository import SystemRunRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)

PublicationPhase = Literal["free", "premium", "all"]


class PublicationService:
    """
    Publie les coupons sur Telegram.

    - FREE → TELEGRAM_FREE_CHANNEL_ID
    - SAFE / VALUE / HIGH_ODDS → TELEGRAM_PREMIUM_GROUP_ID
    """

    PREMIUM_TYPES = frozenset(
        {CouponType.SAFE, CouponType.VALUE, CouponType.HIGH_ODDS}
    )

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.coupons = CouponRepository(session)
        self.system_runs = SystemRunRepository(session)

    async def publish_from_generation(
        self,
        bot: Bot | None,
        coupon_result: CouponGenerationResult | None,
        *,
        phase: PublicationPhase = "all",
        target_date: date | None = None,
        record_run: bool = True,
    ) -> PublicationBatchResult:
        """Publie les coupons produits par le Coupon Generator."""
        batch = PublicationBatchResult()
        day = target_date or self._today()

        if not self.settings.publication_enable:
            log_event(logger, "PUBLICATION_SKIPPED", reason="disabled")
            return batch

        if coupon_result is None:
            return batch

        if bot is None or not self.settings.has_telegram():
            log_event(logger, "PUBLICATION_SKIPPED", reason="no_bot")
            return batch

        run = self.system_runs.start_run(PUBLICATION_RUN_TYPE) if record_run else None
        if run is not None:
            batch.system_run_id = run.id

        for generated in coupon_result.all_coupons():
            if not self._should_publish_type(generated.coupon_type, phase):
                continue
            item = await self._publish_generated_coupon(
                bot,
                generated,
                target_date=day,
            )
            batch.items.append(item)
            if item.skipped and item.reason:
                log_event(
                    logger,
                    "PUBLICATION_SKIPPED",
                    coupon_type=generated.coupon_type.value,
                    reason=item.reason,
                )
            elif not item.success and not item.skipped:
                batch.errors += 1

        if run is not None:
            status = SystemRunStatus.PARTIAL if batch.errors else SystemRunStatus.SUCCESS
            self.system_runs.finish_run(
                run.id,
                status=status,
                processed=batch.published_count,
                error_message=f"errors={batch.errors}" if batch.errors else None,
            )

        log_event(
            logger,
            "TELEGRAM_PUBLICATION_COMPLETED",
            published=batch.published_count,
            confirmed=sum(1 for i in batch.items if i.confirmed_only),
            errors=batch.errors,
        )
        return batch

    async def _publish_generated_coupon(
        self,
        bot: Bot,
        generated,
        *,
        target_date: date,
    ) -> PublishedCouponResult:
        result = PublishedCouponResult(
            coupon_type=generated.coupon_type,
            coupon_id=generated.coupon_id,
        )

        chat_id = self._resolve_chat_id(generated.coupon_type)
        if not chat_id:
            result.skipped = True
            result.reason = "channel_not_configured"
            return result

        if generated.coupon_id is None:
            result.skipped = True
            result.reason = "coupon_not_persisted"
            return result

        coupon = self.coupons.get_coupon_with_details(generated.coupon_id)
        if coupon is None:
            result.skipped = True
            result.reason = "coupon_not_found"
            return result

        result.chat_id = chat_id
        current_fp = selection_fingerprint_from_coupon(coupon)

        if self.settings.publication_confirm_if_unchanged:
            previous = self.coupons.get_latest_published_by_type(
                coupon.type,
                target_date,
                self.settings.timezone,
            )
            if previous is not None and previous.id != coupon.id:
                previous_fp = selection_fingerprint_from_coupon(previous)
                if coupons_unchanged(current_fp, previous_fp):
                    return await self._send_confirmation(
                        bot,
                        chat_id,
                        coupon.type,
                        previous.version,
                        coupon_id=coupon.id,
                    )

        detailed = _resolve_coupon_type(coupon.type) != CouponType.FREE
        text = format_coupon_message(coupon, self.settings, detailed=detailed)

        try:
            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            self.coupons.publish_coupon(coupon.id)
            result.success = True
            result.message_id = message.message_id
            ClvService(self.session, self.settings).record_publication_odds(coupon.id)
            log_event(
                logger,
                "COUPON_PUBLISHED",
                coupon_id=coupon.id,
                coupon_type=_resolve_coupon_type(coupon.type).value,
                chat_id=chat_id,
            )
            return result
        except TelegramError as exc:
            result.reason = str(exc)
            log_event(
                logger,
                "COUPON_PUBLISH_FAILED",
                coupon_id=coupon.id,
                error=str(exc),
            )
            return result

    async def _send_confirmation(
        self,
        bot: Bot,
        chat_id: str,
        coupon_type: CouponType,
        version: int,
        *,
        coupon_id: int,
    ) -> PublishedCouponResult:
        text = format_confirmation_message(coupon_type, version=version)
        result = PublishedCouponResult(
            coupon_type=coupon_type,
            coupon_id=coupon_id,
            chat_id=chat_id,
        )
        try:
            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
            )
            self.coupons.cancel_coupon(
                coupon_id,
                reason="Doublon — contenu identique au coupon publié",
            )
            result.success = True
            result.confirmed_only = True
            result.message_id = message.message_id
            log_event(
                logger,
                "COUPON_CONFIRMED_UNCHANGED",
                coupon_id=coupon_id,
                coupon_type=coupon_type.value,
            )
            return result
        except TelegramError as exc:
            result.reason = str(exc)
            return result

    def _resolve_chat_id(self, coupon_type: CouponType) -> str | None:
        if coupon_type == CouponType.FREE:
            channel = self.settings.telegram_free_channel_id.strip()
            return channel or None
        if coupon_type in self.PREMIUM_TYPES:
            group = self.settings.telegram_premium_group_id.strip()
            return group or None
        return None

    @staticmethod
    def _should_publish_type(coupon_type: CouponType, phase: PublicationPhase) -> bool:
        if phase == "all":
            return True
        if phase == "free":
            return coupon_type == CouponType.FREE
        return coupon_type in PublicationService.PREMIUM_TYPES

    def _today(self) -> date:
        tz = ZoneInfo(self.settings.timezone)
        return datetime.now(tz).date()
