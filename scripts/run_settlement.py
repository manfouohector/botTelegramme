#!/usr/bin/env python
"""Settlement des prédictions et coupons terminés."""

from __future__ import annotations

import argparse
import sys

from app.database.session import get_session_factory
from app.tracking.tracking_engine import TrackingEngine
from app.utils.logging import get_logger

logger = get_logger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Settlement prédictions et coupons")
    parser.add_argument("--match-id", type=int, help="Régler un match spécifique")
    parser.add_argument("--days-back", type=int, help="Fenêtre de recherche (jours)")
    args = parser.parse_args()

    factory = get_session_factory()
    session = factory()
    try:
        engine = TrackingEngine(session)
        if args.match_id:
            results = engine.settle_match(args.match_id)
            session.commit()
            print(f"Match {args.match_id}: {len(results)} prédictions réglées")
            for r in results:
                print(f"  - pred {r.prediction_id}: {'OK' if r.is_correct else 'KO'}")
        else:
            batch = engine.settle_pending(days_back=args.days_back)
            session.commit()
            print(batch.to_dict())
        return 0
    except Exception:
        session.rollback()
        logger.exception("Settlement échoué")
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
