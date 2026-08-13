"""Backtest Engine — évaluation walk-forward sans data leakage."""

from __future__ import annotations

from copy import copy
from datetime import datetime, timezone
from typing import Iterator

from contextlib import contextmanager
from sqlalchemy.orm import Session

from app.backtesting.constants import BACKTEST_RUN_TYPE
from app.backtesting.exceptions import InsufficientBacktestDataError
from app.backtesting.schemas import BacktestComparisonReport, BacktestConfig, BacktestReport
from app.calibration.evaluator import records_from_prediction
from app.calibration.metrics import evaluate_market
from app.calibration.schemas import MarketEvaluationRecord
from app.config.settings import Settings, get_settings
from app.database.enums import SystemRunStatus
from app.prediction.constants import ENGINE_VERSION
from app.prediction.exceptions import InsufficientPredictionDataError, MatchNotFoundError
from app.prediction.prediction_engine import PredictionEngine
from app.repositories.prediction_data_repository import PredictionDataRepository
from app.repositories.system_run_repository import SystemRunRepository
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


def _top1_accuracy(records: list[MarketEvaluationRecord]) -> float:
    if not records:
        return 0.0
    correct = 0
    for record in records:
        if not record.probabilities:
            continue
        predicted = max(record.probabilities, key=record.probabilities.get)
        if predicted == record.actual_selection:
            correct += 1
    return correct / len(records)


class BacktestEngine:
    """
    Teste le modèle sur matchs historiques.

    Anti-leakage : as_of = scheduled_at pour chaque match (via PredictionEngine).
    """

    DEFAULT_VARIANTS = (
        BacktestConfig(label="poisson", enable_dixon_coles=False, enable_ml=False),
        BacktestConfig(label="dixon_coles", enable_dixon_coles=True, enable_ml=False),
        BacktestConfig(
            label="ensemble",
            enable_dixon_coles=True,
            enable_ml=True,
        ),
    )

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.prediction_data = PredictionDataRepository(session)
        self.system_runs = SystemRunRepository(session)

    def run(
        self,
        season_id: int,
        before_date: datetime,
        *,
        config: BacktestConfig | None = None,
        competition_id: int | None = None,
        limit: int | None = None,
        record_run: bool = True,
    ) -> BacktestReport:
        """Backtest avec la configuration courante ou une variante."""
        cfg = config or BacktestConfig(label="default")
        run = self.system_runs.start_run(BACKTEST_RUN_TYPE) if record_run else None

        try:
            report = self._execute_variant(
                season_id,
                before_date,
                cfg,
                competition_id=competition_id,
                limit=limit,
            )
            if run is not None:
                self.system_runs.finish_run(
                    run.id,
                    status=SystemRunStatus.SUCCESS,
                    processed=report.matches_evaluated,
                    predictions_created=report.records_count,
                    error_message=f"variant={cfg.label}",
                )
            log_event(
                logger,
                "BACKTEST_COMPLETED",
                variant=cfg.label,
                matches=report.matches_evaluated,
                accuracy=round(report.top1_accuracy, 4),
            )
            return report
        except Exception as exc:
            if run is not None:
                self.system_runs.finish_run(
                    run.id,
                    status=SystemRunStatus.FAILED,
                    error_message=str(exc),
                )
            raise

    def compare_variants(
        self,
        season_id: int,
        before_date: datetime,
        *,
        variants: list[BacktestConfig] | None = None,
        competition_id: int | None = None,
        limit: int | None = None,
    ) -> BacktestComparisonReport:
        """Compare Poisson, Dixon-Coles, ensemble, etc. sur les mêmes matchs."""
        configs = variants or list(self.DEFAULT_VARIANTS)
        reports: list[BacktestReport] = []
        for cfg in configs:
            reports.append(
                self.run(
                    season_id,
                    before_date,
                    config=cfg,
                    competition_id=competition_id,
                    limit=limit,
                    record_run=False,
                )
            )
        return BacktestComparisonReport(season_id=season_id, variants=reports)

    def _execute_variant(
        self,
        season_id: int,
        before_date: datetime,
        config: BacktestConfig,
        *,
        competition_id: int | None,
        limit: int | None,
    ) -> BacktestReport:
        matches = self.prediction_data.get_season_finished_matches(
            season_id,
            before_date,
            competition_id=competition_id,
        )
        if limit is not None:
            matches = matches[:limit]

        min_matches = self.settings.backtest_min_matches
        if len(matches) < min_matches:
            raise InsufficientBacktestDataError(
                f"Matchs insuffisants ({len(matches)}/{min_matches})"
            )

        records: list[MarketEvaluationRecord] = []
        skipped = 0

        with self._settings_override(config):
            engine = PredictionEngine(self.session, self.settings)
            for match in matches:
                try:
                    prediction = engine.build_prediction(
                        match.id,
                        as_of=match.scheduled_at,
                    )
                    records.extend(records_from_prediction(prediction, match))
                except (MatchNotFoundError, InsufficientPredictionDataError):
                    skipped += 1

        if not records:
            raise InsufficientBacktestDataError("Aucun record d'évaluation produit")

        market_codes = sorted({r.market_code for r in records})
        by_market = {
            code: evaluate_market(records, code, n_bins=self.settings.calibration_bins)
            for code in market_codes
        }

        return BacktestReport(
            variant_label=config.label,
            season_id=season_id,
            matches_evaluated=len(matches) - skipped,
            matches_skipped=skipped,
            records_count=len(records),
            top1_accuracy=_top1_accuracy(records),
            by_market=by_market,
            model_version=ENGINE_VERSION,
            run_at=datetime.now(timezone.utc),
        )

    @contextmanager
    def _settings_override(self, config: BacktestConfig) -> Iterator[None]:
        """Applique temporairement les flags d'une variante."""
        previous = self.settings
        base = copy(previous)
        if config.enable_dixon_coles is not None:
            base.prediction_enable_dixon_coles = config.enable_dixon_coles
        if config.enable_ml is not None:
            base.prediction_enable_ml = config.enable_ml
        if config.enable_calibration is not None:
            base.calibration_enable = config.enable_calibration
        self.settings = base
        try:
            yield
        finally:
            self.settings = previous
