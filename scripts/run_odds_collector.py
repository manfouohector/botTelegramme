#!/usr/bin/env python
"""CLI — collecte des cotes The Odds API."""

from __future__ import annotations

import argparse
import sys

from app.config.settings import get_settings
from app.database.session import session_scope
from app.utils.logging import setup_logging
from app.value.odds_collector import OddsCollector


def main() -> int:
    setup_logging()
    settings = get_settings()

    parser = argparse.ArgumentParser(description="Collecte cotes bookmakers (The Odds API)")
    parser.add_argument("--sport", help="Clé sport Odds API (ex: soccer_france_ligue_one)")
    parser.add_argument("--match-id", type=int, help="ID match interne (optionnel)")
    args = parser.parse_args()

    sport_keys = [args.sport] if args.sport else settings.get_odds_api_sport_keys()
    if not sport_keys:
        print("Erreur : spécifier --sport ou ODDS_API_SPORT_KEYS dans .env", file=sys.stderr)
        return 1

    if not settings.has_odds_api():
        print("Erreur : ODDS_API_KEY non configuré", file=sys.stderr)
        return 1

    with session_scope() as session:
        collector = OddsCollector(session, settings)
        try:
            for sport_key in sport_keys:
                if args.match_id:
                    count = collector.collect_for_match(args.match_id, sport_key)
                    print(f"Match {args.match_id} : {count} cotes collectées ({sport_key})")
                else:
                    result = collector.collect_for_sport(sport_key)
                    print(
                        f"{sport_key} : {result['events']} événements, "
                        f"{result['odds']} cotes, {result['linked']} matchs liés"
                    )
        finally:
            collector.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
