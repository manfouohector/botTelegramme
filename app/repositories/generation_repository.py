"""Requêtes SQL pour génération et statut admin."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.database.enums import CouponStatus, CouponType, MatchStatus
from app.models.coupon import Coupon, CouponPrediction
from app.models.match import Match
from app.models.prediction import Prediction, PredictionResult
from app.models.system import SystemRun


def day_bounds(target_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    """Bornes [début, fin] du jour dans le timezone configuré."""
    tz = ZoneInfo(timezone_name)
    start = datetime.combine(target_date, time.min, tzinfo=tz)
    end = datetime.combine(target_date, time.max, tzinfo=tz)
    return start, end


class GenerationRepository:
    """Accès PostgreSQL pour pipeline et statut."""

    COUPON_TYPES = (
        CouponType.FREE,
        CouponType.SAFE,
        CouponType.VALUE,
        CouponType.HIGH_ODDS,
    )

    PUBLISHED_STATUSES = (
        CouponStatus.PUBLISHED,
        CouponStatus.CONFIRMED,
        CouponStatus.SETTLED,
    )

    def __init__(self, session: Session):
        self.session = session

    def get_scheduled_matches_for_date(self, target_date: date, timezone_name: str) -> list[Match]:
        start, end = day_bounds(target_date, timezone_name)
        return list(
            self.session.scalars(
                select(Match)
                .options(
                    selectinload(Match.home_team),
                    selectinload(Match.away_team),
                )
                .where(
                    Match.scheduled_at >= start,
                    Match.scheduled_at <= end,
                    Match.status == MatchStatus.SCHEDULED,
                )
                .order_by(Match.scheduled_at.asc())
            ).all()
        )

    def get_matches_starting_within_minutes(
        self,
        minutes: int,
        timezone_name: str,
    ) -> list[Match]:
        """Matchs SCHEDULED dont le coup d'envoi est dans les N prochaines minutes."""
        tz = ZoneInfo(timezone_name)
        now = datetime.now(tz)
        window_end = now + timedelta(minutes=minutes)
        return list(
            self.session.scalars(
                select(Match)
                .options(
                    selectinload(Match.home_team),
                    selectinload(Match.away_team),
                )
                .where(
                    Match.status == MatchStatus.SCHEDULED,
                    Match.scheduled_at >= now,
                    Match.scheduled_at <= window_end,
                )
                .order_by(Match.scheduled_at.asc())
            ).all()
        )

    def count_matches_for_date(self, target_date: date, timezone_name: str) -> int:
        start, end = day_bounds(target_date, timezone_name)
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(Match)
                .where(Match.scheduled_at >= start, Match.scheduled_at <= end)
            )
            or 0
        )

    def get_coupons_for_date(self, target_date: date, timezone_name: str) -> list[Coupon]:
        start, end = day_bounds(target_date, timezone_name)
        return list(
            self.session.scalars(
                select(Coupon)
                .options(
                    selectinload(Coupon.predictions).selectinload(CouponPrediction.prediction),
                )
                .where(Coupon.created_at >= start, Coupon.created_at <= end)
                .order_by(Coupon.created_at.asc())
            ).all()
        )

    def get_latest_coupon_by_type(
        self,
        coupon_type: CouponType,
        target_date: date,
        timezone_name: str,
    ) -> Coupon | None:
        coupons = self.get_coupons_for_date(target_date, timezone_name)
        typed = [c for c in coupons if c.type == coupon_type]
        return typed[-1] if typed else None

    def any_coupon_published_for_date(self, target_date: date, timezone_name: str) -> bool:
        coupons = self.get_coupons_for_date(target_date, timezone_name)
        return any(c.status in self.PUBLISHED_STATUSES for c in coupons)

    def get_settled_selection_stats_for_date(
        self,
        target_date: date,
        timezone_name: str,
    ) -> dict[CouponType, tuple[int, int]]:
        """Retourne (gagnées, total) par type de coupon pour une date de match."""
        start, end = day_bounds(target_date, timezone_name)
        stats: dict[CouponType, tuple[int, int]] = {
            ctype: (0, 0) for ctype in self.COUPON_TYPES
        }

        rows = self.session.execute(
            select(
                Coupon.type,
                PredictionResult.is_correct,
            )
            .join(CouponPrediction, CouponPrediction.coupon_id == Coupon.id)
            .join(Prediction, Prediction.id == CouponPrediction.prediction_id)
            .join(PredictionResult, PredictionResult.prediction_id == Prediction.id)
            .join(Match, Match.id == Prediction.match_id)
            .where(
                Match.scheduled_at >= start,
                Match.scheduled_at <= end,
                Coupon.status == CouponStatus.SETTLED,
            )
        ).all()

        for coupon_type, is_correct in rows:
            won, total = stats[coupon_type]
            stats[coupon_type] = (won + int(bool(is_correct)), total + 1)

        return stats

    def find_latest_settled_match_day(self, timezone_name: str) -> date | None:
        """Dernière date (timezone) avec au moins une sélection réglée en coupon."""
        row = self.session.scalar(
            select(func.max(Match.scheduled_at))
            .join(Prediction, Prediction.match_id == Match.id)
            .join(PredictionResult, PredictionResult.prediction_id == Prediction.id)
            .join(CouponPrediction, CouponPrediction.prediction_id == Prediction.id)
            .join(Coupon, Coupon.id == CouponPrediction.coupon_id)
            .where(Coupon.status == CouponStatus.SETTLED)
        )
        if row is None:
            return None
        if isinstance(row, datetime):
            if row.tzinfo is None:
                row = row.replace(tzinfo=timezone.utc)
            return row.astimezone(ZoneInfo(timezone_name)).date()
        return None

    def get_latest_generation_run(self, run_type: str) -> SystemRun | None:
        return self.session.scalar(
            select(SystemRun)
            .where(SystemRun.run_type == run_type)
            .order_by(SystemRun.started_at.desc())
            .limit(1)
        )

    def get_generation_run_for_date(
        self,
        run_type: str,
        target_date: date,
        timezone_name: str,
    ) -> SystemRun | None:
        start, end = day_bounds(target_date, timezone_name)
        return self.session.scalar(
            select(SystemRun)
            .where(
                SystemRun.run_type == run_type,
                SystemRun.started_at >= start,
                SystemRun.started_at <= end,
            )
            .order_by(SystemRun.started_at.desc())
            .limit(1)
        )
