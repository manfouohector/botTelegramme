"""Persistance des exécutions système."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.enums import SystemRunStatus
from app.models.system import SystemRun


class SystemRunRepository:
    """Accès PostgreSQL pour system_runs."""

    def __init__(self, session: Session):
        self.session = session

    def start_run(self, run_type: str) -> SystemRun:
        run = SystemRun(run_type=run_type, status=SystemRunStatus.RUNNING)
        self.session.add(run)
        self.session.flush()
        return run

    def finish_run(
        self,
        run_id: int,
        *,
        status: SystemRunStatus,
        processed: int = 0,
        predictions_created: int = 0,
        coupons_created: int = 0,
        error_message: str | None = None,
    ) -> SystemRun | None:
        run = self.session.get(SystemRun, run_id)
        if run is None:
            return None
        run.status = status
        run.finished_at = datetime.now(timezone.utc)
        run.matches_processed = processed
        run.predictions_created = predictions_created
        run.coupons_created = coupons_created
        run.error_message = error_message
        self.session.flush()
        return run

    def get_latest_run(self, run_type: str) -> SystemRun | None:
        from sqlalchemy import select

        return self.session.scalar(
            select(SystemRun)
            .where(SystemRun.run_type == run_type)
            .order_by(SystemRun.started_at.desc())
            .limit(1)
        )
