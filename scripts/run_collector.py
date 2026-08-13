"""Script CLI pour lancer le Data Collector."""

import argparse
import sys

from app.collectors.data_collector import DataCollector
from app.config.settings import get_settings
from app.database.session import reset_engine, session_scope
from app.utils.logging import setup_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Data Collector Sportmonks")
    parser.add_argument("--date", help="Date cible YYYY-MM-DD (défaut: aujourd'hui)")
    parser.add_argument("--start", help="Date début plage YYYY-MM-DD")
    parser.add_argument("--end", help="Date fin plage YYYY-MM-DD")
    parser.add_argument("--force", action="store_true", help="Ignorer le cache TTL")
    args = parser.parse_args()

    settings = get_settings()
    setup_logging(settings)

    try:
        with session_scope(settings) as session, DataCollector(session, settings) as collector:
            if args.start and args.end:
                result = collector.collect_between(args.start, args.end, force=args.force)
            else:
                result = collector.collect_for_date(args.date, force=args.force)
    except Exception as exc:
        print(f"Erreur : {exc}", file=sys.stderr)
        return 1
    finally:
        reset_engine()

    print(f"Date       : {result.date}")
    print(f"Récupérés  : {result.fetched}")
    print(f"Stockés    : {result.stored}")
    print(f"Cache OK   : {result.skipped_fresh}")
    print(f"Hors ligue : {result.skipped_league}")
    print(f"Placeholder: {result.skipped_placeholder}")
    print(f"Erreurs    : {result.errors}")
    print(f"Requêtes   : {result.api_requests}")

    if result.error_messages:
        print("\nDétails erreurs :")
        for msg in result.error_messages[:10]:
            print(f"  - {msg}")

    return 1 if result.errors and result.stored == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
