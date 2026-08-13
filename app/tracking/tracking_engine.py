"""Tracking Engine — settlement + historique + métriques."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.config.settings import Settings, get_settings
from app.database.enums import CouponStatus, MatchStatus
from app.models.coupon import Coupon
from app.models.prediction import Prediction
from app.repositories.tracking_repository import TrackingRepository
from app.tracking.constants import TRACKING_ENGINE_VERSION
from app.tracking.exceptions import CouponNotSettleableError, MatchNotSettleableError
from app.tracking.metrics import aggregate_metrics, calculate_clv, unit_stake_profit
from app.tracking.outcome_resolver import resolve_market_outcome
from app.tracking.schemas import (
    CouponSettlementResult,
    HistoryEntry,
    SettlementBatchResult,
    SettlementResult,
    TrackingMetrics,
)
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class TrackingEngine:
    """
    Settlement des prédictions et coupons + métriques de performance.

    Ne supprime jamais les mauvais résultats — transparence totale.
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.repo = TrackingRepository(session)

    def settle_prediction(self, prediction: Prediction) -> SettlementResult | None:
        """Règle une prédiction si le match est terminé."""
        existing = prediction.result or self.repo.get_prediction_result(prediction.id)
        if existing is not None:
            market_code = prediction.market.code if prediction.market else ""
            return SettlementResult(
                prediction_id=prediction.id,
                match_id=prediction.match_id,
                market_code=market_code,
                selection=prediction.selection,
                actual_result=existing.actual_result,
                is_correct=existing.is_correct,
                clv=float(existing.clv) if existing.clv is not None else None,
                already_settled=True,
            )

        match = prediction.match or self.repo.get_match(prediction.match_id)
        if match is None or not _is_settleable_match(match):
            return None

        market_code = prediction.market.code if prediction.market else ""
        actual = resolve_market_outcome(market_code, match.home_score, match.away_score)
        is_correct = prediction.selection == actual

        clv = None
        if prediction.odds is not None:
            closing = self.repo.get_closing_odds(
                prediction.match_id,
                prediction.market_id,
                prediction.selection,
            )
            if closing is not None:
                clv = calculate_clv(float(prediction.odds), closing)

        saved = self.repo.save_prediction_result(
            prediction.id,
            actual_result=actual,
            is_correct=is_correct,
            clv=clv,
        )

        return SettlementResult(
            prediction_id=prediction.id,
            match_id=prediction.match_id,
            market_code=market_code,
            selection=prediction.selection,
            actual_result=saved.actual_result,
            is_correct=saved.is_correct,
            clv=clv,
        )

    def settle_match(self, match_id: int) -> list[SettlementResult]:
        """Règle toutes les prédictions non réglées d'un match."""
        match = self.repo.get_match(match_id)
        if match is None:
            raise MatchNotSettleableError(f"Match {match_id} introuvable")
        if not _is_settleable_match(match):
            raise MatchNotSettleableError(
                f"Match {match_id} non réglable (status={match.status.value})"
            )

        results: list[SettlementResult] = []
        for prediction in self.repo.get_unsettled_predictions_for_match(match_id):
            settled = self.settle_prediction(prediction)
            if settled is not None:
                results.append(settled)
        return results

    def settle_pending(self, *, days_back: int | None = None) -> SettlementBatchResult:
        """Batch : règle matchs terminés puis coupons éligibles."""
        window = days_back if days_back is not None else self.settings.tracking_settle_days_back
        batch = SettlementBatchResult()

        for match in self.repo.get_finished_matches_pending_settlement(days_back=window):
            try:
                for result in self.settle_match(match.id):
                    batch.prediction_results.append(result)
                    if not result.already_settled:
                        batch.predictions_settled += 1
                    else:
                        batch.predictions_skipped += 1
            except MatchNotSettleableError:
                batch.predictions_skipped += 1

        for coupon in self.repo.get_coupons_pending_settlement():
            try:
                coupon_result = self.settle_coupon(coupon)
                batch.coupon_results.append(coupon_result)
                if coupon_result.already_settled:
                    batch.coupons_skipped += 1
                else:
                    batch.coupons_settled += 1
            except CouponNotSettleableError:
                batch.coupons_skipped += 1

        log_event(
            logger,
            "SETTLEMENT_BATCH",
            predictions=batch.predictions_settled,
            coupons=batch.coupons_settled,
            engine=TRACKING_ENGINE_VERSION,
        )
        return batch

    def settle_coupon(self, coupon: Coupon) -> CouponSettlementResult:
        """Règle un coupon accumulé (toutes les sélections doivent être correctes)."""
        if coupon.status == CouponStatus.SETTLED:
            return _coupon_result_from_status(coupon, already_settled=True)

        if coupon.status not in TrackingRepository.SETTLEABLE_COUPON_STATUSES:
            raise CouponNotSettleableError(
                f"Coupon {coupon.id} non réglable (status={coupon.status.value})"
            )

        links = sorted(coupon.predictions, key=lambda link: link.position)
        if not links:
            raise CouponNotSettleableError(f"Coupon {coupon.id} sans prédictions")

        combined_odds = 1.0
        correct_count = 0
        for link in links:
            prediction = link.prediction
            result_row = self.repo.get_prediction_result(prediction.id)
            if result_row is None:
                settled = self.settle_prediction(prediction)
                if settled is None:
                    raise CouponNotSettleableError(
                        f"Prédiction {prediction.id} non réglable pour coupon {coupon.id}"
                    )
                result_row = self.repo.get_prediction_result(prediction.id)

            if result_row is None:
                raise CouponNotSettleableError(
                    f"Prédiction {prediction.id} toujours sans résultat"
                )

            if prediction.odds is not None:
                combined_odds *= float(prediction.odds)
            if result_row.is_correct:
                correct_count += 1

        is_won = correct_count == len(links)
        profit = unit_stake_profit(is_correct=is_won, decimal_odds=combined_odds)

        coupon.status = CouponStatus.SETTLED
        self.session.flush()

        return CouponSettlementResult(
            coupon_id=coupon.id,
            coupon_type=coupon.type,
            is_won=is_won,
            selections_total=len(links),
            selections_correct=correct_count,
            combined_odds=combined_odds,
            theoretical_profit=profit,
        )

    def get_metrics(
        self,
        *,
        days_back: int | None = None,
        coupon_type=None,
        market_code: str | None = None,
    ) -> TrackingMetrics:
        """Calcule accuracy, ROI, Brier, Log Loss, CLV et breakdowns."""
        records = self.repo.get_settled_metric_records(
            days_back=days_back,
            coupon_type=coupon_type,
            market_code=market_code,
        )
        return aggregate_metrics(records)

    def get_history(
        self,
        *,
        limit: int | None = None,
        coupon_type=None,
        days_back: int | None = None,
    ) -> list[HistoryEntry]:
        """Historique des prédictions réglées."""
        return self.repo.get_history(
            limit=limit or self.settings.tracking_history_limit,
            coupon_type=coupon_type,
            days_back=days_back,
        )


def _is_settleable_match(match) -> bool:
    if match.status != MatchStatus.FINISHED:
        return False
    return match.home_score is not None and match.away_score is not None


def _coupon_result_from_status(coupon: Coupon, *, already_settled: bool) -> CouponSettlementResult:
    links = sorted(coupon.predictions, key=lambda link: link.position)
    combined_odds = 1.0
    correct_count = 0
    for link in links:
        pred = link.prediction
        if pred.odds is not None:
            combined_odds *= float(pred.odds)
        result = pred.result
        if result and result.is_correct:
            correct_count += 1
    is_won = len(links) > 0 and correct_count == len(links)
    return CouponSettlementResult(
        coupon_id=coupon.id,
        coupon_type=coupon.type,
        is_won=is_won,
        selections_total=len(links),
        selections_correct=correct_count,
        combined_odds=combined_odds,
        theoretical_profit=unit_stake_profit(is_correct=is_won, decimal_odds=combined_odds),
        already_settled=already_settled,
    )
