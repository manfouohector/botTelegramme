"""Configuration APScheduler — tâches planifiées."""

from __future__ import annotations

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config.settings import Settings, get_settings
from app.jobs.constants import ALL_JOBS
from app.jobs.tasks import (
    parse_hhmm,
    run_daily_analysis_async,
    run_final_analysis_async,
    run_maintenance,
    run_results_collection,
    run_settlement,
    run_subscription_expiration_job,
)
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)


def _wrap_async(coro_fn, settings: Settings):
    """Adaptateur APScheduler pour coroutines."""
    import asyncio

    def runner():
        asyncio.run(coro_fn(settings))

    return runner


def create_scheduler(settings: Settings | None = None) -> BlockingScheduler:
    """Construit le scheduler avec toutes les tâches configurées."""
    cfg = settings or get_settings()
    tz = cfg.timezone
    scheduler = BlockingScheduler(timezone=tz)

    daily_h, daily_m = parse_hhmm(cfg.daily_analysis_time)
    scheduler.add_job(
        _wrap_async(run_daily_analysis_async, cfg),
        CronTrigger(hour=daily_h, minute=daily_m, timezone=tz),
        id="daily_analysis",
        name="Analyse quotidienne (FREE)",
        replace_existing=True,
    )

    scheduler.add_job(
        _wrap_async(run_final_analysis_async, cfg),
        IntervalTrigger(minutes=cfg.final_analysis_check_interval_minutes, timezone=tz),
        id="final_analysis",
        name="Analyse finale (Premium)",
        replace_existing=True,
    )

    results_h, results_m = parse_hhmm(cfg.results_collection_time)
    scheduler.add_job(
        lambda: run_results_collection(cfg),
        CronTrigger(hour=results_h, minute=results_m, timezone=tz),
        id="results_collection",
        name="Récupération résultats",
        replace_existing=True,
    )

    settle_h, settle_m = parse_hhmm(cfg.settlement_time)
    scheduler.add_job(
        lambda: run_settlement(cfg),
        CronTrigger(hour=settle_h, minute=settle_m, timezone=tz),
        id="settlement",
        name="Settlement prédictions",
        replace_existing=True,
    )

    exp_h, exp_m = parse_hhmm(cfg.subscription_expiration_time)

    async def _expiration_job(settings: Settings):
        await run_subscription_expiration_job(
            settings,
            notify=settings.subscription_expiration_notify,
        )

    scheduler.add_job(
        _wrap_async(_expiration_job, cfg),
        CronTrigger(hour=exp_h, minute=exp_m, timezone=tz),
        id="subscription_expiration",
        name="Expiration abonnements",
        replace_existing=True,
    )

    scheduler.add_job(
        lambda: run_maintenance(cfg),
        CronTrigger(hour=3, minute=0, timezone=tz),
        id="maintenance",
        name="Maintenance système",
        replace_existing=True,
    )

    return scheduler


def start_scheduler(settings: Settings | None = None) -> None:
    """Démarre le scheduler bloquant (processus dédié)."""
    cfg = settings or get_settings()
    setup_logging(cfg)

    if not cfg.scheduler_enable:
        logger.warning("SCHEDULER_DISABLED | scheduler_enable=false")
        return

    scheduler = create_scheduler(cfg)
    jobs = scheduler.get_jobs()
    logger.info(
        "SCHEDULER_STARTING | timezone=%s jobs=%s",
        cfg.timezone,
        [job.id for job in jobs],
    )
    for job in jobs:
        logger.info("SCHEDULER_JOB | id=%s next=%s", job.id, job.next_run_time)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("SCHEDULER_STOPPED")


def list_scheduled_jobs(settings: Settings | None = None) -> list[dict]:
    """Liste les jobs configurés (sans démarrer le scheduler)."""
    cfg = settings or get_settings()
    scheduler = create_scheduler(cfg)
    return [
        {
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
    ]
