#!/usr/bin/env python3
"""Script CLI — génération quotidienne pipeline complet."""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date

from telegram import Bot

from app.config.settings import get_settings
from app.database.session import get_session_factory
from app.services.generation_service import GenerationService
from app.services.publication_service import PublicationService
from app.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def _run_async(args: argparse.Namespace) -> int:
    settings = get_settings()
    configure_logging(settings)

    target_date: date | None = None
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error("Date invalide: %s (attendu YYYY-MM-DD)", args.date)
            return 1

    session_factory = get_session_factory(settings)
    session = session_factory()
    bot = Bot(settings.telegram_bot_token.strip()) if settings.has_telegram() else None

    try:
        result = GenerationService(session, settings).run(
            target_date=target_date,
            skip_collector=args.skip_collector or not settings.has_sportmonks(),
            skip_odds_collector=args.skip_odds or not settings.has_odds_api(),
            persist_coupons=not args.no_persist,
        )

        if (
            args.publish
            and settings.publication_enable
            and bot is not None
            and result.coupon_result is not None
        ):
            pub = await PublicationService(session, settings).publish_from_generation(
                bot,
                result.coupon_result,
                phase=args.phase,
                target_date=result.target_date,
            )
            result.publication_result = pub
            result.published = pub.any_published or pub.any_confirmed

        session.commit()
        logger.info(
            "GENERATION_DONE | date=%s predictions=%s coupons=%s published=%s status=%s",
            result.target_date,
            result.predictions_created,
            result.coupons_created,
            result.published,
            result.status.value,
        )
        return 0 if result.status.value != "FAILED" else 1
    except Exception:
        session.rollback()
        logger.exception("GENERATION_SCRIPT_FAILED")
        return 1
    finally:
        session.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Lance le pipeline de génération quotidienne")
    parser.add_argument("--date", type=str, help="Date cible YYYY-MM-DD (défaut: aujourd'hui)")
    parser.add_argument(
        "--skip-collector",
        action="store_true",
        help="Ignorer la collecte Sportmonks",
    )
    parser.add_argument(
        "--skip-odds",
        action="store_true",
        help="Ignorer la collecte Odds API",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Ne pas persister les coupons en base",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publier sur Telegram après génération",
    )
    parser.add_argument(
        "--phase",
        choices=("free", "premium", "all"),
        default="all",
        help="Phase de publication (free=canal, premium=groupe)",
    )
    args = parser.parse_args()
    return asyncio.run(_run_async(args))


if __name__ == "__main__":
    sys.exit(main())
