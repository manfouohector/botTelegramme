"""Persistance et requêtes Tracking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, selectinload

from app.database.enums import CouponStatus, CouponType, MatchStatus
from app.models.coupon import Coupon, CouponPrediction
from app.models.market import Market, Odd
from app.models.match import Match
from app.models.prediction import Prediction, PredictionResult
from app.tracking.schemas import HistoryEntry, MetricRecord


class TrackingRepository:
    """Accès PostgreSQL pour settlement et historique."""

    SETTLEABLE_COUPON_STATUSES = (
        CouponStatus.PUBLISHED,
        CouponStatus.CONFIRMED,
    )

    def __init__(self, session: Session):
        self.session = session

    def get_match(self, match_id: int) -> Match | None:
        return self.session.get(Match, match_id)

    def get_finished_matches_pending_settlement(self, *, days_back: int = 7) -> list[Match]:
        """Matchs terminés avec prédictions non réglées."""
        since = datetime.now(timezone.utc) - timedelta(days=days_back)
        settled_ids = select(PredictionResult.prediction_id)

        pending_match_ids = (
            select(Prediction.match_id)
            .outerjoin(PredictionResult, Prediction.id == PredictionResult.prediction_id)
            .where(
                PredictionResult.id.is_(None),
                Prediction.match_id == Match.id,
            )
        )

        return list(
            self.session.scalars(
                select(Match)
                .where(
                    Match.status == MatchStatus.FINISHED,
                    Match.home_score.is_not(None),
                    Match.away_score.is_not(None),
                    Match.scheduled_at >= since,
                    pending_match_ids.exists(),
                )
                .order_by(Match.scheduled_at.desc())
            ).all()
        )

    def get_unsettled_predictions_for_match(self, match_id: int) -> list[Prediction]:
        return list(
            self.session.scalars(
                select(Prediction)
                .options(
                    selectinload(Prediction.market),
                    selectinload(Prediction.match),
                    selectinload(Prediction.result),
                )
                .outerjoin(PredictionResult, Prediction.id == PredictionResult.prediction_id)
                .where(
                    Prediction.match_id == match_id,
                    PredictionResult.id.is_(None),
                )
            ).all()
        )

    def get_prediction_with_relations(self, prediction_id: int) -> Prediction | None:
        return self.session.scalar(
            select(Prediction)
            .options(
                selectinload(Prediction.market),
                selectinload(Prediction.match),
                selectinload(Prediction.result),
            )
            .where(Prediction.id == prediction_id)
        )

    def get_prediction_result(self, prediction_id: int) -> PredictionResult | None:
        return self.session.scalar(
            select(PredictionResult).where(PredictionResult.prediction_id == prediction_id)
        )

    def get_closing_odds(
        self,
        match_id: int,
        market_id: int,
        selection: str,
    ) -> float | None:
        """Récupère la cote de clôture si disponible."""
        row = self.session.scalar(
            select(Odd)
            .where(
                Odd.match_id == match_id,
                Odd.market_id == market_id,
                Odd.selection == selection,
            )
            .order_by(Odd.fetched_at.desc())
            .limit(1)
        )
        if row is None:
            return None
        if row.closing_odds is not None:
            return float(row.closing_odds)
        return float(row.odds)

    def save_prediction_result(
        self,
        prediction_id: int,
        *,
        actual_result: str,
        is_correct: bool,
        clv: float | None = None,
    ) -> PredictionResult:
        existing = self.session.scalar(
            select(PredictionResult).where(PredictionResult.prediction_id == prediction_id)
        )
        if existing is not None:
            return existing

        result = PredictionResult(
            prediction_id=prediction_id,
            actual_result=actual_result,
            is_correct=is_correct,
            clv=Decimal(str(round(clv, 6))) if clv is not None else None,
            settled_at=datetime.now(timezone.utc),
        )
        self.session.add(result)
        self.session.flush()
        return result

    def get_coupons_pending_settlement(self) -> list[Coupon]:
        return list(
            self.session.scalars(
                select(Coupon)
                .options(
                    selectinload(Coupon.predictions)
                    .selectinload(CouponPrediction.prediction)
                    .selectinload(Prediction.result),
                    selectinload(Coupon.predictions)
                    .selectinload(CouponPrediction.prediction)
                    .selectinload(Prediction.market),
                    selectinload(Coupon.predictions)
                    .selectinload(CouponPrediction.prediction)
                    .selectinload(Prediction.match),
                )
                .where(Coupon.status.in_(self.SETTLEABLE_COUPON_STATUSES))
                .order_by(Coupon.created_at.desc())
            ).all()
        )

    def get_settled_metric_records(
        self,
        *,
        days_back: int | None = None,
        coupon_type: CouponType | None = None,
        market_code: str | None = None,
    ) -> list[MetricRecord]:
        stmt = (
            select(
                PredictionResult.is_correct,
                Prediction.probability,
                Prediction.odds,
                PredictionResult.clv,
                Market.code,
                Prediction.model_version,
                Coupon.type,
            )
            .join(Prediction, PredictionResult.prediction_id == Prediction.id)
            .join(Market, Prediction.market_id == Market.id)
            .outerjoin(CouponPrediction, CouponPrediction.prediction_id == Prediction.id)
            .outerjoin(Coupon, Coupon.id == CouponPrediction.coupon_id)
        )

        if days_back is not None:
            since = datetime.now(timezone.utc) - timedelta(days=days_back)
            stmt = stmt.where(PredictionResult.settled_at >= since)
        if coupon_type is not None:
            stmt = stmt.where(Coupon.type == coupon_type)
        if market_code is not None:
            stmt = stmt.where(Market.code == market_code.upper())

        rows = self.session.execute(stmt).all()
        records: list[MetricRecord] = []
        for is_correct, probability, odds, clv, code, model_version, ctype in rows:
            records.append(
                MetricRecord(
                    is_correct=bool(is_correct),
                    probability=float(probability),
                    decimal_odds=float(odds) if odds is not None else None,
                    clv=float(clv) if clv is not None else None,
                    market_code=code,
                    coupon_type=ctype.value if ctype is not None else None,
                    model_version=model_version,
                )
            )
        return records

    def get_history(
        self,
        *,
        limit: int = 50,
        coupon_type: CouponType | None = None,
        days_back: int | None = None,
    ) -> list[HistoryEntry]:
        stmt = (
            select(PredictionResult)
            .join(Prediction, PredictionResult.prediction_id == Prediction.id)
            .options(
                selectinload(PredictionResult.prediction).selectinload(Prediction.market),
                selectinload(PredictionResult.prediction)
                .selectinload(Prediction.match)
                .selectinload(Match.home_team),
                selectinload(PredictionResult.prediction)
                .selectinload(Prediction.match)
                .selectinload(Match.away_team),
                selectinload(PredictionResult.prediction)
                .selectinload(Prediction.coupon_links)
                .selectinload(CouponPrediction.coupon),
            )
            .order_by(PredictionResult.settled_at.desc())
            .limit(limit)
        )

        if coupon_type is not None:
            stmt = (
                stmt.join(CouponPrediction, CouponPrediction.prediction_id == Prediction.id)
                .join(Coupon, Coupon.id == CouponPrediction.coupon_id)
                .where(Coupon.type == coupon_type)
            )
        if days_back is not None:
            since = datetime.now(timezone.utc) - timedelta(days=days_back)
            stmt = stmt.where(PredictionResult.settled_at >= since)

        entries: list[HistoryEntry] = []
        for result in self.session.scalars(stmt).all():
            pred = result.prediction
            if pred is None or pred.market is None:
                continue
            coupon = pred.coupon_links[0].coupon if pred.coupon_links else None
            match = pred.match
            entries.append(
                HistoryEntry(
                    prediction_id=pred.id,
                    match_id=pred.match_id,
                    market_code=pred.market.code,
                    selection=pred.selection,
                    actual_result=result.actual_result,
                    is_correct=result.is_correct,
                    probability=float(pred.probability),
                    decimal_odds=float(pred.odds) if pred.odds is not None else None,
                    clv=float(result.clv) if result.clv is not None else None,
                    model_version=pred.model_version,
                    settled_at=result.settled_at,
                    coupon_id=coupon.id if coupon else None,
                    coupon_type=coupon.type if coupon else None,
                    home_team=match.home_team.name if match and match.home_team else "",
                    away_team=match.away_team.name if match and match.away_team else "",
                )
            )
        return entries
