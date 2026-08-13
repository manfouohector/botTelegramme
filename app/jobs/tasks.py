"""Exécution des tâches planifiées (cron)."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import Bot

from app.collectors.data_collector import DataCollector
from app.config.settings import Settings, get_settings
from app.database.enums import SystemRunStatus
from app.database.session import check_database_connection, session_scope
from app.jobs.constants import (
    DAILY_ANALYSIS_RUN_TYPE,
    FINAL_ANALYSIS_RUN_TYPE,
    JOB_DAILY_ANALYSIS,
    JOB_FINAL_ANALYSIS,
    JOB_MAINTENANCE,
    JOB_RESULTS_COLLECTION,
    JOB_SETTLEMENT,
    JOB_SUBSCRIPTION_EXPIRATION,
    MAINTENANCE_RUN_TYPE,
    RESULTS_COLLECTION_RUN_TYPE,
    SETTLEMENT_RUN_TYPE,
)
from app.jobs.schemas import JobResult
from app.jobs.subscription_expiration import run_subscription_expiration_async
from app.repositories.generation_repository import GenerationRepository
from app.repositories.system_run_repository import SystemRunRepository
from app.services.generation_service import GenerationService
from app.services.publication_service import PublicationService
from app.tracking.tracking_engine import TrackingEngine
from app.utils.logging import get_logger, log_event, setup_logging

logger = get_logger(__name__)


def parse_hhmm(value: str) -> tuple[int, int]:
    """Parse HH:MM en (heure, minute)."""
    hour, minute = value.split(":")
    return int(hour), int(minute)


async def _publish_generation(
    session,
    settings: Settings,
    batch,
    *,
    phase: str,
) -> None:
    if not settings.publication_enable or not settings.has_telegram():
        batch.publication_deferred = True
        return
    if batch.coupon_result is None:
        return
    bot = Bot(settings.telegram_bot_token.strip())
    pub = await PublicationService(session, settings).publish_from_generation(
        bot,
        batch.coupon_result,
        phase=phase,
        target_date=batch.target_date,
        record_run=False,
    )
    batch.publication_result = pub
    batch.published = pub.any_published or pub.any_confirmed
    batch.publication_deferred = False


def _run_already_today(session, run_type: str, timezone_name: str) -> bool:
    repo = SystemRunRepository(session)
    run = repo.get_latest_run(run_type)
    if run is None or run.started_at is None:
        return False
    tz = ZoneInfo(timezone_name)
    started = run.started_at
    if started.tzinfo is None:
        started = started.replace(tzinfo=ZoneInfo("UTC"))
    today = datetime.now(tz).date()
    return started.astimezone(tz).date() == today


async def run_daily_analysis_async(settings: Settings | None = None) -> JobResult:
    """TASK 1 — analyse matinale + coupon FREE + publication canal."""
    cfg = settings or get_settings()
    setup_logging(cfg)
    result = JobResult(job_name=JOB_DAILY_ANALYSIS)

    if not cfg.has_database():
        result.success = False
        result.reason = "database_not_configured"
        return result

    with session_scope(cfg) as session:
        if _run_already_today(session, DAILY_ANALYSIS_RUN_TYPE, cfg.timezone):
            result.skipped = True
            result.reason = "already_ran_today"
            return result

        gen = GenerationService(session, cfg).run(
            phase="free",
            run_type=DAILY_ANALYSIS_RUN_TYPE,
            skip_collector=not cfg.has_sportmonks(),
            skip_odds_collector=not cfg.has_odds_api(),
        )
        await _publish_generation(session, cfg, gen, phase="free")

        result.success = gen.status != SystemRunStatus.FAILED
        result.system_run_id = gen.system_run_id
        result.details = gen.to_dict()

    log_event(logger, "JOB_DAILY_ANALYSIS_COMPLETED", success=result.success)
    return result


async def run_final_analysis_async(settings: Settings | None = None) -> JobResult:
    """TASK 2 — mise à jour avant matchs + coupons Premium."""
    cfg = settings or get_settings()
    setup_logging(cfg)
    result = JobResult(job_name=JOB_FINAL_ANALYSIS)

    if not cfg.has_database():
        result.success = False
        result.reason = "database_not_configured"
        return result

    with session_scope(cfg) as session:
        repo = GenerationRepository(session)
        upcoming = repo.get_matches_starting_within_minutes(
            cfg.final_analysis_minutes_before,
            cfg.timezone,
        )
        if not upcoming:
            result.skipped = True
            result.reason = "no_matches_in_window"
            return result

        if _run_already_today(session, FINAL_ANALYSIS_RUN_TYPE, cfg.timezone):
            result.skipped = True
            result.reason = "already_ran_today"
            return result

        gen = GenerationService(session, cfg).run(
            phase="premium",
            run_type=FINAL_ANALYSIS_RUN_TYPE,
            skip_collector=not cfg.has_sportmonks(),
            skip_odds_collector=not cfg.has_odds_api(),
            force_collector=True,
        )
        await _publish_generation(session, cfg, gen, phase="premium")

        result.success = gen.status != SystemRunStatus.FAILED
        result.system_run_id = gen.system_run_id
        result.details = {
            **gen.to_dict(),
            "matches_in_window": len(upcoming),
        }

    log_event(logger, "JOB_FINAL_ANALYSIS_COMPLETED", success=result.success)
    return result


def run_results_collection(settings: Settings | None = None) -> JobResult:
    """TASK 3 — récupération des résultats (scores, statuts)."""
    cfg = settings or get_settings()
    setup_logging(cfg)
    result = JobResult(job_name=JOB_RESULTS_COLLECTION)

    if not cfg.has_database():
        result.success = False
        result.reason = "database_not_configured"
        return result
    if not cfg.has_sportmonks():
        result.skipped = True
        result.reason = "sportmonks_not_configured"
        return result

    tz = ZoneInfo(cfg.timezone)
    today = datetime.now(tz).date()
    yesterday = today - timedelta(days=1)

    with session_scope(cfg) as session:
        runs = SystemRunRepository(session)
        run = runs.start_run(RESULTS_COLLECTION_RUN_TYPE)
        result.system_run_id = run.id

        stored = 0
        errors = 0
        try:
            with DataCollector(session, cfg) as collector:
                for day in (yesterday, today):
                    collection = collector.collect_for_date(day.isoformat(), force=True)
                    stored += collection.stored
                    errors += collection.errors
            runs.finish_run(
                run.id,
                status=SystemRunStatus.PARTIAL if errors else SystemRunStatus.SUCCESS,
                processed=stored,
                error_message=f"errors={errors}" if errors else None,
            )
            result.details = {"stored": stored, "errors": errors}
            result.success = errors == 0 or stored > 0
        except Exception as exc:
            runs.finish_run(run.id, status=SystemRunStatus.FAILED, error_message=str(exc))
            result.success = False
            result.reason = str(exc)
            logger.exception("JOB_RESULTS_COLLECTION_FAILED")

    log_event(logger, "JOB_RESULTS_COLLECTION_COMPLETED", stored=result.details.get("stored", 0))
    return result


def run_settlement(settings: Settings | None = None) -> JobResult:
    """TASK 4 — settlement prédictions et coupons."""
    cfg = settings or get_settings()
    setup_logging(cfg)
    result = JobResult(job_name=JOB_SETTLEMENT)

    if not cfg.has_database():
        result.success = False
        result.reason = "database_not_configured"
        return result

    with session_scope(cfg) as session:
        runs = SystemRunRepository(session)
        run = runs.start_run(SETTLEMENT_RUN_TYPE)
        result.system_run_id = run.id
        try:
            batch = TrackingEngine(session, cfg).settle_pending()
            runs.finish_run(
                run.id,
                status=SystemRunStatus.SUCCESS,
                processed=batch.predictions_settled + batch.coupons_settled,
            )
            result.details = batch.to_dict() if hasattr(batch, "to_dict") else {
                "predictions_settled": batch.predictions_settled,
                "coupons_settled": batch.coupons_settled,
            }
        except Exception as exc:
            runs.finish_run(run.id, status=SystemRunStatus.FAILED, error_message=str(exc))
            result.success = False
            result.reason = str(exc)
            logger.exception("JOB_SETTLEMENT_FAILED")

    log_event(logger, "JOB_SETTLEMENT_COMPLETED", success=result.success)
    return result


async def run_subscription_expiration_job(
    settings: Settings | None = None,
    *,
    notify: bool = True,
) -> JobResult:
    """TASK 5 — expiration abonnements Premium."""
    cfg = settings or get_settings()
    setup_logging(cfg)
    details = await run_subscription_expiration_async(cfg, notify=notify)
    return JobResult(
        job_name=JOB_SUBSCRIPTION_EXPIRATION,
        success=details.get("errors", 0) == 0,
        system_run_id=details.get("system_run_id"),
        details=details,
    )


def run_maintenance(settings: Settings | None = None) -> JobResult:
    """TASK 6 — maintenance légère (santé DB, logs)."""
    cfg = settings or get_settings()
    setup_logging(cfg)
    result = JobResult(job_name=JOB_MAINTENANCE)

    db_ok = check_database_connection(cfg)
    result.details = {
        "database_ok": db_ok,
        "app_env": cfg.app_env,
        "timezone": cfg.timezone,
    }
    result.success = db_ok

    if cfg.has_database():
        with session_scope(cfg) as session:
            runs = SystemRunRepository(session)
            run = runs.start_run(MAINTENANCE_RUN_TYPE)
            result.system_run_id = run.id
            status = SystemRunStatus.SUCCESS if db_ok else SystemRunStatus.FAILED
            runs.finish_run(
                run.id,
                status=status,
                error_message=None if db_ok else "database_unreachable",
            )

    log_event(logger, "JOB_MAINTENANCE_COMPLETED", database_ok=db_ok)
    return result


def run_job_sync(job_name: str, settings: Settings | None = None) -> JobResult:
    """Exécute un job par nom (CLI / cron externe)."""
    cfg = settings or get_settings()
    if job_name == JOB_DAILY_ANALYSIS:
        return asyncio.run(run_daily_analysis_async(cfg))
    if job_name == JOB_FINAL_ANALYSIS:
        return asyncio.run(run_final_analysis_async(cfg))
    if job_name == JOB_RESULTS_COLLECTION:
        return run_results_collection(cfg)
    if job_name == JOB_SETTLEMENT:
        return run_settlement(cfg)
    if job_name == JOB_SUBSCRIPTION_EXPIRATION:
        return asyncio.run(run_subscription_expiration_job(cfg))
    if job_name == JOB_MAINTENANCE:
        return run_maintenance(cfg)
    raise ValueError(f"Job inconnu : {job_name}")
