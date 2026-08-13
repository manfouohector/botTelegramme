"""Orchestration pipeline génération quotidienne (/generate)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

from typing import Literal

from sqlalchemy.orm import Session

from app.calibration.calibration_engine import CalibrationEngine
from app.collectors.data_collector import DataCollector
from app.config.settings import Settings, get_settings
from app.coupons.candidate_builder import build_candidates_from_analyses
from app.coupons.coupon_generator import CouponGenerator
from app.coupons.schemas import GeneratedCoupon
from app.database.enums import CouponStatus, SystemRunStatus
from app.generation.constants import GENERATION_RUN_TYPE
from app.generation.exceptions import GenerationStageError
from app.generation.schemas import GenerationBatchResult, encode_run_metadata
from app.prediction.exceptions import (
    InsufficientPredictionDataError,
    MatchNotFoundError,
    PredictionEngineError,
)
from app.prediction.prediction_engine import PredictionEngine
from app.repositories.generation_repository import GenerationRepository
from app.repositories.system_run_repository import SystemRunRepository
from app.risk.risk_engine import RiskEngine
from app.utils.logging import get_logger, log_event
from app.value.exceptions import OddsNotFoundError, ValueEngineError
from app.value.odds_collector import OddsCollector
from app.value.value_engine import ValueEngine

logger = get_logger(__name__)

GenerationPhase = Literal["all", "free", "premium"]


class GenerationService:
    """
    Pipeline complet :
    Collector → Features/Prediction → Calibration → Value → Risk → Coupons.

    La publication Telegram est gérée par PublicationService (Module 18).
    """

    def __init__(self, session: Session, settings: Settings | None = None):
        self.session = session
        self.settings = settings or get_settings()
        self.repo = GenerationRepository(session)
        self.system_runs = SystemRunRepository(session)
        self.prediction_engine = PredictionEngine(session, self.settings)
        self.calibration_engine = CalibrationEngine(
            session, self.settings, prediction_engine=self.prediction_engine
        )
        self.value_engine = ValueEngine(session, self.settings)
        self.risk_engine = RiskEngine(session, self.settings)
        self.coupon_generator = CouponGenerator(session, self.settings)

    def run(
        self,
        *,
        target_date: date | None = None,
        phase: GenerationPhase = "all",
        run_type: str = GENERATION_RUN_TYPE,
        skip_collector: bool = False,
        skip_odds_collector: bool = False,
        force_collector: bool = False,
        record_run: bool = True,
        persist_coupons: bool = True,
    ) -> GenerationBatchResult:
        """Exécute le pipeline pour une date (défaut = aujourd'hui timezone)."""
        day = target_date or self._today()
        batch = GenerationBatchResult(target_date=day)

        run = self.system_runs.start_run(run_type) if record_run else None
        if run is not None:
            batch.system_run_id = run.id

        try:
            if not skip_collector:
                self._run_collector(day, batch, force=force_collector)
            else:
                batch.matches_fetched = self.repo.count_matches_for_date(
                    day, self.settings.timezone
                )

            if not skip_odds_collector:
                self._run_odds_collector(batch)

            matches = self.repo.get_scheduled_matches_for_date(day, self.settings.timezone)
            batch.matches_analyzed = len(matches)

            if not matches:
                batch.status = SystemRunStatus.SUCCESS
                self._finish_run(run, batch)
                log_event(logger, "GENERATION_COMPLETED", date=str(day), coupons=0)
                return batch

            analyses = self._analyze_matches(matches, batch)
            candidates = build_candidates_from_analyses(self.session, analyses)
            coupon_result = self._generate_coupons(
                candidates,
                phase=phase,
                persist=persist_coupons,
            )
            batch.coupon_result = coupon_result
            batch.coupons_created = coupon_result.coupons_created
            batch.skip_reasons = self._collect_skip_reasons(coupon_result)

            batch.status = (
                SystemRunStatus.PARTIAL
                if batch.failed_stage or batch.error_message
                else SystemRunStatus.SUCCESS
            )
            self._finish_run(run, batch)
            log_event(
                logger,
                "GENERATION_COMPLETED",
                date=str(day),
                predictions=batch.predictions_created,
                coupons=batch.coupons_created,
            )
            return batch

        except GenerationStageError as exc:
            batch.failed_stage = exc.stage
            batch.error_message = f"{exc.stage}: {exc.message}"
            batch.status = SystemRunStatus.FAILED
            self._finish_run(run, batch)
            log_event(
                logger,
                "GENERATION_FAILED",
                stage=exc.stage,
                error=exc.message,
            )
            return batch
        except Exception as exc:
            batch.failed_stage = batch.failed_stage or "UNKNOWN"
            batch.error_message = str(exc)
            batch.status = SystemRunStatus.FAILED
            self._finish_run(run, batch)
            logger.exception("GENERATION_FAILED | date=%s", day)
            return batch

    def _today(self) -> date:
        tz = ZoneInfo(self.settings.timezone)
        return datetime.now(tz).date()

    def _run_collector(self, day: date, batch: GenerationBatchResult, *, force: bool = False) -> None:
        if not self.settings.has_sportmonks():
            raise GenerationStageError(
                "DATA_COLLECTION",
                "SPORTMONKS_API_TOKEN non configuré",
            )
        try:
            with DataCollector(self.session, self.settings) as collector:
                result = collector.collect_for_date(day.isoformat(), force=force)
            batch.matches_fetched = result.stored + result.skipped_fresh
            if result.errors and result.stored == 0 and result.skipped_fresh == 0:
                detail = result.error_messages[0] if result.error_messages else "collecte échouée"
                raise GenerationStageError("DATA_COLLECTION", detail)
        except GenerationStageError:
            raise
        except Exception as exc:
            raise GenerationStageError("DATA_COLLECTION", str(exc)) from exc

    def _run_odds_collector(self, batch: GenerationBatchResult) -> None:
        if not self.settings.has_odds_api():
            log_event(logger, "ODDS_COLLECTION_SKIPPED", reason="no_api_key")
            return
        sport_keys = self.settings.get_odds_api_sport_keys()
        if not sport_keys:
            log_event(logger, "ODDS_COLLECTION_SKIPPED", reason="no_sport_keys")
            return
        try:
            with OddsCollector(self.session, self.settings) as collector:
                for sport_key in sport_keys:
                    collector.collect_for_sport(sport_key)
        except Exception as exc:
            batch.failed_stage = "ODDS_COLLECTION"
            batch.error_message = f"ODDS_COLLECTION: {exc}"
            log_event(logger, "ODDS_COLLECTION_WARNING", error=str(exc))

    def _analyze_matches(
        self,
        matches: list,
        batch: GenerationBatchResult,
    ) -> list:
        self.calibration_engine.load()
        analyses: list = []

        for match in matches:
            try:
                prediction = self.prediction_engine.build_prediction(
                    match.id,
                    persist=True,
                )
                batch.predictions_created += 1

                calibrated = self.calibration_engine.calibrate(prediction)
                value_analysis = self.value_engine.analyze(calibrated)
                risk = self.risk_engine.assess(calibrated, value_analysis)
                analyses.append((calibrated.raw, value_analysis, risk))
            except (MatchNotFoundError, InsufficientPredictionDataError) as exc:
                log_event(logger, "GENERATION_MATCH_SKIPPED", match_id=match.id, reason=str(exc))
            except OddsNotFoundError as exc:
                log_event(logger, "GENERATION_MATCH_SKIPPED", match_id=match.id, reason=str(exc))
            except (ValueEngineError, PredictionEngineError) as exc:
                log_event(logger, "GENERATION_MATCH_ERROR", match_id=match.id, error=str(exc))
            except Exception:
                logger.exception("GENERATION_MATCH_ERROR | match_id=%s", match.id)

        return analyses

    def _generate_coupons(
        self,
        candidates: list,
        *,
        phase: GenerationPhase,
        persist: bool,
    ):
        status = CouponStatus.DRAFT
        if phase == "free":
            return self.coupon_generator.generate_free_only(candidates, persist=persist)
        if phase == "premium":
            return self.coupon_generator.generate_premium_only(candidates, persist=persist)
        return self.coupon_generator.generate(candidates, persist=persist, status=status)

    @staticmethod
    def _collect_skip_reasons(coupon_result) -> dict[str, str]:
        reasons: dict[str, str] = {}
        for generated in (
            coupon_result.free,
            coupon_result.safe,
            coupon_result.value,
            coupon_result.high_odds,
        ):
            if isinstance(generated, GeneratedCoupon) and generated.skipped and generated.skip_reason:
                reasons[generated.coupon_type.value] = generated.skip_reason
        return reasons

    def _finish_run(self, run, batch: GenerationBatchResult) -> None:
        if run is None:
            return
        meta = encode_run_metadata(skip_reasons=batch.skip_reasons)
        error_message = batch.error_message or meta
        if batch.error_message and meta:
            error_message = batch.error_message
        elif meta:
            error_message = meta

        self.system_runs.finish_run(
            run.id,
            status=batch.status,
            processed=batch.matches_analyzed,
            predictions_created=batch.predictions_created,
            coupons_created=batch.coupons_created,
            error_message=error_message,
        )
