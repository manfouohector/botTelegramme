#!/usr/bin/env python3
"""Processus scheduler — toutes les tâches planifiées."""

from __future__ import annotations

import argparse
import json
import sys

from app.config.settings import get_settings
from app.jobs.constants import ALL_JOBS
from app.jobs.scheduler import list_scheduled_jobs, start_scheduler
from app.jobs.tasks import run_job_sync
from app.utils.logging import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Scheduler APScheduler — bot football")
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister les jobs configurés et quitter",
    )
    parser.add_argument(
        "--run",
        choices=ALL_JOBS,
        help="Exécuter un job immédiatement puis quitter",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings)

    if args.list:
        print(json.dumps(list_scheduled_jobs(settings), indent=2, ensure_ascii=False))
        return 0

    if args.run:
        result = run_job_sync(args.run, settings)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        return 0 if result.success or result.skipped else 1

    if not settings.scheduler_enable:
        print("Scheduler désactivé (SCHEDULER_ENABLE=false)", file=sys.stderr)
        return 1

    start_scheduler(settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
