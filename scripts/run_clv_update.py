#!/usr/bin/env python3
"""CLI — mise à jour cotes de clôture pour CLV."""

from __future__ import annotations

import argparse
import json
import sys

from app.backtesting.clv_service import ClvService
from app.config.settings import get_settings
from app.database.session import session_scope
from app.utils.logging import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Mise à jour closing odds (CLV)")
    parser.add_argument(
        "--hours-before",
        type=int,
        help="Fenêtre avant coup d'envoi (défaut: CLV_UPDATE_HOURS_BEFORE_KICKOFF)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Afficher l'analyse CLV agrégée",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings)

    with session_scope(settings) as session:
        service = ClvService(session, settings)
        updated = service.refresh_closing_odds(hours_before=args.hours_before)
        result = {"closing_odds_updated": updated}
        if args.analyze:
            result["analysis"] = service.analyze_published_clv().to_dict()

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
