#!/usr/bin/env python3
"""CLI — backtesting walk-forward."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from app.backtesting.backtest_engine import BacktestEngine
from app.backtesting.model_registry import ModelRegistry
from app.config.settings import get_settings
from app.database.session import session_scope
from app.utils.logging import configure_logging


def main() -> int:
    parser = argparse.ArgumentParser(description="Backtest walk-forward (sans data leakage)")
    parser.add_argument("--season-id", type=int, required=True)
    parser.add_argument(
        "--before",
        type=str,
        help="Date limite ISO (défaut: maintenant UTC)",
    )
    parser.add_argument("--limit", type=int, help="Nombre max de matchs")
    parser.add_argument(
        "--compare",
        action="store_true",
        help="Comparer Poisson / Dixon-Coles / Ensemble",
    )
    parser.add_argument(
        "--register",
        action="store_true",
        help="Enregistrer les résultats dans le Model Registry",
    )
    args = parser.parse_args()

    settings = get_settings()
    configure_logging(settings)

    before = (
        datetime.fromisoformat(args.before).replace(tzinfo=timezone.utc)
        if args.before
        else datetime.now(timezone.utc)
    )
    limit = args.limit or settings.backtest_default_limit

    with session_scope(settings) as session:
        engine = BacktestEngine(session, settings)
        if args.compare:
            report = engine.compare_variants(args.season_id, before, limit=limit)
            output = report.to_dict()
        else:
            single = engine.run(args.season_id, before, limit=limit)
            output = single.to_dict()
            if args.register:
                ModelRegistry(session, settings).register_backtest(single)

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
