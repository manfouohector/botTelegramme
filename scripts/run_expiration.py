#!/usr/bin/env python
"""Expiration automatique des abonnements Premium."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config.settings import get_settings
from app.database.session import reset_engine, session_scope
from app.jobs.subscription_expiration import run_subscription_expiration_async
from app.services.expiration_service import SubscriptionExpirationService
from app.utils.logging import setup_logging


async def _run_db_only() -> dict:
    settings = get_settings()
    setup_logging(settings)
    with session_scope(settings) as session:
        result = SubscriptionExpirationService(session, settings).expire_due_subscriptions()
        return result.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser(description="Expiration abonnements Premium")
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Expire en base sans Telegram (retrait groupe / notification)",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Ne pas envoyer de message privé aux utilisateurs expirés",
    )
    args = parser.parse_args()

    try:
        if args.db_only:
            result = asyncio.run(_run_db_only())
        else:
            result = asyncio.run(
                run_subscription_expiration_async(notify=not args.no_notify)
            )
        print(result)
        return 0
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    finally:
        reset_engine()


if __name__ == "__main__":
    sys.exit(main())
