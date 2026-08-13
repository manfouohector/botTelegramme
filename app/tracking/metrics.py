"""Métriques de performance — accuracy, ROI, Brier, Log Loss, CLV."""

from __future__ import annotations

from collections import defaultdict

from app.calibration.metrics import binary_brier, binary_log_loss
from app.tracking.schemas import MetricRecord, PerformanceBreakdown, TrackingMetrics


def calculate_clv(bet_odds: float, closing_odds: float) -> float:
    """CLV = (cote prise / cote clôture) - 1."""
    if closing_odds <= 0:
        return 0.0
    return (bet_odds / closing_odds) - 1.0


def unit_stake_profit(*, is_correct: bool, decimal_odds: float | None) -> float:
    """Profit théorique pour une mise unitaire."""
    if not is_correct:
        return -1.0
    if decimal_odds is None or decimal_odds <= 1.0:
        return 0.0
    return decimal_odds - 1.0


def aggregate_metrics(records: list[MetricRecord]) -> TrackingMetrics:
    """Agrège les métriques globales et par dimension."""
    if not records:
        return TrackingMetrics(sample_size=0, accuracy=0.0, roi=0.0)

    correct = sum(1 for r in records if r.is_correct)
    accuracy = correct / len(records)
    roi = sum(unit_stake_profit(is_correct=r.is_correct, decimal_odds=r.decimal_odds) for r in records) / len(
        records
    )

    brier_values = [binary_brier(r.probability, r.is_correct) for r in records]
    log_loss_values = [binary_log_loss(r.probability, r.is_correct) for r in records]
    clv_values = [r.clv for r in records if r.clv is not None]

    by_market = _breakdown(records, key=lambda r: r.market_code)
    by_coupon = _breakdown(
        [r for r in records if r.coupon_type],
        key=lambda r: r.coupon_type or "UNKNOWN",
    )
    by_model = _breakdown(records, key=lambda r: r.model_version)

    return TrackingMetrics(
        sample_size=len(records),
        accuracy=accuracy,
        roi=roi,
        avg_brier=sum(brier_values) / len(brier_values),
        avg_log_loss=sum(log_loss_values) / len(log_loss_values),
        avg_clv=sum(clv_values) / len(clv_values) if clv_values else None,
        by_market=by_market,
        by_coupon_type=by_coupon,
        by_model_version=by_model,
    )


def _breakdown(
    records: list[MetricRecord],
    *,
    key,
) -> list[PerformanceBreakdown]:
    groups: dict[str, list[MetricRecord]] = defaultdict(list)
    for record in records:
        groups[key(record)].append(record)

    result: list[PerformanceBreakdown] = []
    for group_key, items in sorted(groups.items()):
        correct = sum(1 for r in items if r.is_correct)
        brier = [binary_brier(r.probability, r.is_correct) for r in items]
        log_loss = [binary_log_loss(r.probability, r.is_correct) for r in items]
        clv_vals = [r.clv for r in items if r.clv is not None]
        result.append(
            PerformanceBreakdown(
                key=group_key,
                sample_size=len(items),
                accuracy=correct / len(items),
                roi=sum(unit_stake_profit(is_correct=r.is_correct, decimal_odds=r.decimal_odds) for r in items)
                / len(items),
                avg_brier=sum(brier) / len(brier),
                avg_log_loss=sum(log_loss) / len(log_loss),
                avg_clv=sum(clv_vals) / len(clv_vals) if clv_vals else None,
            )
        )
    return result
