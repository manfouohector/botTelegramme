"""CLV — opening vs closing odds."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.backtesting.constants import CLV_UPDATE_RUN_TYPE
from app.backtesting.schemas import ClvAnalysisReport
from app.config.settings import Settings, get_settings
from app.database.enums import CouponStatus, MatchStatus, SystemRunStatus
from app.models.coupon import Coupon, CouponPrediction
from app.models.match import Match
from app.models.prediction import Prediction, PredictionResult
from app.repositories.odds_repository import OddsRepository
from app.repositories.system_run_repository import SystemRunRepository
from app.tracking.metrics import calculate_clv
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class ClvService:
    """
    Gère opening/published odds et closing odds pour le CLV.

    CLV = (cote publiée / cote clôture) - 1
    """

    PUBLISHED_STATUSES = (
        CouponStatus.PUBLISHED,
        CouponStatus.CONFIRMED,
        CouponStatus.SETTLED,
    )

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.odds = OddsRepository(session)
        self.system_runs = SystemRunRepository(session)

    def record_publication_odds(self, coupon_id: int) -> int:
        """Capture les cotes au moment de la publication."""
        coupon = self.session.scalar(
            select(Coupon)
            .options(
                selectinload(Coupon.predictions)
                .selectinload(CouponPrediction.prediction)
                .selectinload(Prediction.market),
            )
            .where(Coupon.id == coupon_id)
        )
        if coupon is None:
            return 0

        updated = 0
        for link in coupon.predictions:
            pred = link.prediction
            if pred is None or pred.market is None:
                continue
            snapshot = self.odds.get_market_odds_snapshot(
                pred.match_id,
                bookmaker=self.settings.odds_preferred_bookmaker or None,
            )
            market_odds = snapshot.get(pred.market.code, {})
            odd_row = market_odds.get(pred.selection)
            if odd_row is None:
                continue

            if pred.odds is None:
                pred.odds = odd_row.odds
            if odd_row.opening_odds is None:
                odd_row.opening_odds = pred.odds or odd_row.odds
            updated += 1

        self.session.flush()
        log_event(logger, "CLV_OPENING_RECORDED", coupon_id=coupon_id, predictions=updated)
        return updated

    def refresh_closing_odds(self, *, hours_before: int | None = None) -> int:
        """Met à jour closing_odds pour les matchs imminents."""
        window = hours_before or self.settings.clv_update_hours_before_kickoff
        tz = timezone.utc
        now = datetime.now(tz)
        horizon = now + timedelta(hours=window)

        matches = list(
            self.session.scalars(
                select(Match).where(
                    Match.status == MatchStatus.SCHEDULED,
                    Match.scheduled_at >= now,
                    Match.scheduled_at <= horizon,
                )
            ).all()
        )

        run = self.system_runs.start_run(CLV_UPDATE_RUN_TYPE)
        updated = 0
        try:
            for match in matches:
                updated += self._update_match_closing_odds(match.id)
            self.system_runs.finish_run(
                run.id,
                status=SystemRunStatus.SUCCESS,
                processed=updated,
            )
        except Exception as exc:
            self.system_runs.finish_run(run.id, status=SystemRunStatus.FAILED, error_message=str(exc))
            raise

        log_event(logger, "CLV_CLOSING_UPDATED", matches=len(matches), odds=updated)
        return updated

    def _update_match_closing_odds(self, match_id: int) -> int:
        rows = self.odds.get_latest_odds_for_match(match_id)
        count = 0
        for row in rows:
            if row.closing_odds is None:
                row.closing_odds = row.odds
                count += 1
        self.session.flush()
        return count

    def compute_clv_for_prediction(self, prediction_id: int) -> float | None:
        pred = self.session.scalar(
            select(Prediction)
            .options(selectinload(Prediction.market))
            .where(Prediction.id == prediction_id)
        )
        if pred is None or pred.odds is None or pred.market is None:
            return None
        closing = self.odds.get_closing_odds(pred.match_id, pred.market_id, pred.selection)
        if closing is None:
            return None
        return calculate_clv(float(pred.odds), closing)

    def analyze_published_clv(self, *, days_back: int | None = None) -> ClvAnalysisReport:
        """Analyse CLV sur prédictions publiées réglées."""
        window = days_back if days_back is not None else self.settings.tracking_settle_days_back
        since = datetime.now(timezone.utc) - timedelta(days=window)

        rows = self.session.execute(
            select(
                Prediction.odds,
                PredictionResult.clv,
            )
            .join(PredictionResult, PredictionResult.prediction_id == Prediction.id)
            .join(CouponPrediction, CouponPrediction.prediction_id == Prediction.id)
            .join(Coupon, Coupon.id == CouponPrediction.coupon_id)
            .where(
                Coupon.status.in_(self.PUBLISHED_STATUSES),
                PredictionResult.settled_at >= since,
                Prediction.odds.is_not(None),
            )
        ).all()

        if not rows:
            return ClvAnalysisReport()

        clv_values = [float(clv) for _, clv in rows if clv is not None]
        opening = [float(odds) for odds, _ in rows if odds is not None]

        return ClvAnalysisReport(
            sample_size=len(rows),
            avg_clv=sum(clv_values) / len(clv_values) if clv_values else None,
            positive_clv_rate=(
                sum(1 for v in clv_values if v > 0) / len(clv_values) if clv_values else None
            ),
            avg_opening_odds=sum(opening) / len(opening) if opening else None,
        )
