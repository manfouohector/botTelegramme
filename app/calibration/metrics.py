"""Métriques de calibration — Brier, Log Loss, ECE."""

from __future__ import annotations

import math

from app.calibration.schemas import CalibrationBin, MarketEvaluationRecord, MarketMetrics


def multiclass_brier(probabilities: dict[str, float], actual_selection: str) -> float:
    """Brier score multiclasse."""
    return sum(
        (prob - (1.0 if selection == actual_selection else 0.0)) ** 2
        for selection, prob in probabilities.items()
    )


def multiclass_log_loss(probabilities: dict[str, float], actual_selection: str) -> float:
    """Log loss multiclasse."""
    eps = 1e-15
    prob = probabilities.get(actual_selection, eps)
    return -math.log(max(min(prob, 1.0 - eps), eps))


def binary_brier(probability: float, actual: bool) -> float:
    outcome = 1.0 if actual else 0.0
    return (probability - outcome) ** 2


def binary_log_loss(probability: float, actual: bool) -> float:
    eps = 1e-15
    p = max(min(probability, 1.0 - eps), eps)
    if actual:
        return -math.log(p)
    return -math.log(1.0 - p)


def expected_calibration_error(
    records: list[MarketEvaluationRecord],
    *,
    n_bins: int = 10,
) -> tuple[float, list[CalibrationBin]]:
    """
    ECE binaire sur la probabilité de l'issue réelle.

    Pour chaque record, on prend P(actual_selection).
    """
    if not records:
        return 0.0, []

    pairs: list[tuple[float, float]] = []
    for record in records:
        prob = record.probabilities.get(record.actual_selection)
        if prob is None:
            continue
        pairs.append((prob, 1.0))

    if not pairs:
        return 0.0, []

    bins = _build_calibration_bins(pairs, n_bins=n_bins)
    total = sum(b.count for b in bins)
    if total == 0:
        return 0.0, bins

    ece = sum(abs(b.avg_predicted - b.avg_actual) * b.count for b in bins) / total
    return ece, bins


def evaluate_market(
    records: list[MarketEvaluationRecord],
    market_code: str,
    *,
    n_bins: int = 10,
) -> MarketMetrics:
    """Calcule Brier, Log Loss et ECE pour un marché."""
    market_records = [r for r in records if r.market_code == market_code]
    if not market_records:
        return MarketMetrics(
            market_code=market_code,
            sample_size=0,
            brier_score=0.0,
            log_loss=0.0,
            expected_calibration_error=0.0,
        )

    brier = sum(
        multiclass_brier(r.probabilities, r.actual_selection) for r in market_records
    ) / len(market_records)
    log_loss = sum(
        multiclass_log_loss(r.probabilities, r.actual_selection) for r in market_records
    ) / len(market_records)
    ece, bins = expected_calibration_error(market_records, n_bins=n_bins)

    return MarketMetrics(
        market_code=market_code,
        sample_size=len(market_records),
        brier_score=brier,
        log_loss=log_loss,
        expected_calibration_error=ece,
        calibration_bins=bins,
    )


def _build_calibration_bins(
    pairs: list[tuple[float, float]],
    *,
    n_bins: int,
) -> list[CalibrationBin]:
    """Construit les bins de calibration."""
    bins: list[list[tuple[float, float]]] = [[] for _ in range(n_bins)]
    for prob, outcome in pairs:
        idx = min(int(prob * n_bins), n_bins - 1)
        bins[idx].append((prob, outcome))

    result: list[CalibrationBin] = []
    for i, bucket in enumerate(bins):
        if not bucket:
            result.append(
                CalibrationBin(
                    bin_lower=i / n_bins,
                    bin_upper=(i + 1) / n_bins,
                    avg_predicted=0.0,
                    avg_actual=0.0,
                    count=0,
                )
            )
            continue
        avg_pred = sum(p for p, _ in bucket) / len(bucket)
        avg_actual = sum(o for _, o in bucket) / len(bucket)
        result.append(
            CalibrationBin(
                bin_lower=i / n_bins,
                bin_upper=(i + 1) / n_bins,
                avg_predicted=avg_pred,
                avg_actual=avg_actual,
                count=len(bucket),
            )
        )
    return result
