"""Helpers tests Module 17 — génération / statut / historique."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.enums import (
    CouponStatus,
    CouponType,
    MatchStatus,
    SystemRunStatus,
)
from app.generation.constants import GENERATION_RUN_TYPE
from app.generation.schemas import encode_run_metadata
from app.models.coupon import Coupon, CouponPrediction
from app.models.football import Competition, Season, Team
from app.models.market import Market
from app.models.match import Match
from app.models.prediction import AIModel, Prediction, PredictionResult
from app.models.system import SystemRun
from app.prediction.constants import MARKET_1X2, SELECTION_HOME


def seed_status_day(
    session: Session,
    *,
    day: datetime,
    timezone_name: str = "UTC",
) -> dict:
    """Crée un run de génération + coupons FREE/SAFE pour une date."""
    from zoneinfo import ZoneInfo

    local_day = day.astimezone(ZoneInfo(timezone_name)).date()
    run = SystemRun(
        run_type=GENERATION_RUN_TYPE,
        status=SystemRunStatus.SUCCESS,
        matches_processed=18,
        predictions_created=42,
        coupons_created=2,
        error_message=encode_run_metadata(
            skip_reasons={
                "HIGH_ODDS": "aucune sélection n'a passé le Risk Engine.",
            }
        ),
        started_at=day,
        finished_at=day + timedelta(minutes=5),
    )
    session.add(run)
    session.flush()

    comp = Competition(external_id=901, name="Test League", country="Test")
    session.add(comp)
    session.flush()
    season = Season(competition_id=comp.id, external_id=902, name="2026", is_current=True)
    session.add(season)
    session.flush()
    home = Team(external_id=903, name="Home FC")
    away = Team(external_id=904, name="Away FC")
    session.add_all([home, away])
    session.flush()

    match = Match(
        external_match_id=905001,
        competition_id=comp.id,
        season_id=season.id,
        home_team_id=home.id,
        away_team_id=away.id,
        scheduled_at=day,
        status=MatchStatus.SCHEDULED,
    )
    session.add(match)
    session.flush()

    market = Market(code=MARKET_1X2, name="1X2")
    session.add(market)
    session.flush()

    model = AIModel(name="test", version="1.0", type="statistical", active=True)
    session.add(model)
    session.flush()

    free = Coupon(type=CouponType.FREE, status=CouponStatus.PUBLISHED, version=1)
    safe = Coupon(type=CouponType.SAFE, status=CouponStatus.DRAFT, version=1)
    session.add_all([free, safe])
    session.flush()
    free.created_at = day
    free.updated_at = day
    safe.created_at = day
    safe.updated_at = day
    session.flush()

    for coupon, selection in ((free, SELECTION_HOME), (safe, SELECTION_HOME)):
        pred = Prediction(
            match_id=match.id,
            market_id=market.id,
            model_id=model.id,
            model_version="test",
            selection=selection,
            probability=Decimal("0.650000"),
            odds=Decimal("1.5000"),
        )
        session.add(pred)
        session.flush()
        session.add(
            CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=1)
        )

    session.flush()
    return {
        "run": run,
        "day": local_day,
        "free": free,
        "safe": safe,
        "match": match,
    }


def seed_history_day(session: Session, *, day: datetime) -> dict:
    """Crée des coupons réglés avec résultats pour /history."""
    comp = Competition(external_id=801, name="Hist League", country="Test")
    session.add(comp)
    session.flush()
    season = Season(competition_id=comp.id, external_id=802, name="2026", is_current=True)
    session.add(season)
    session.flush()
    home = Team(external_id=803, name="Alpha")
    away = Team(external_id=804, name="Beta")
    session.add_all([home, away])
    session.flush()

    match = Match(
        external_match_id=805001,
        competition_id=comp.id,
        season_id=season.id,
        home_team_id=home.id,
        away_team_id=away.id,
        scheduled_at=day,
        status=MatchStatus.FINISHED,
        home_score=2,
        away_score=0,
    )
    session.add(match)
    session.flush()

    market = Market(code=MARKET_1X2, name="1X2")
    session.add(market)
    session.flush()

    model = AIModel(name="test", version="1.0", type="statistical", active=True)
    session.add(model)
    session.flush()

    configs = [
        (CouponType.FREE, 3, 3),
        (CouponType.SAFE, 4, 4),
        (CouponType.VALUE, 2, 3),
        (CouponType.HIGH_ODDS, 4, 6),
    ]

    coupons = []
    for coupon_type, won, total in configs:
        coupon = Coupon(type=coupon_type, status=CouponStatus.SETTLED, version=1)
        session.add(coupon)
        session.flush()
        coupons.append(coupon)

        for pos in range(1, total + 1):
            is_correct = pos <= won
            pred = Prediction(
                match_id=match.id,
                market_id=market.id,
                model_id=model.id,
                model_version="test",
                selection=SELECTION_HOME if is_correct else "AWAY",
                probability=Decimal("0.600000"),
                odds=Decimal("1.8000"),
            )
            session.add(pred)
            session.flush()
            session.add(
                CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=pos)
            )
            session.add(
                PredictionResult(
                    prediction_id=pred.id,
                    actual_result=SELECTION_HOME,
                    is_correct=is_correct,
                    settled_at=day + timedelta(hours=3),
                )
            )

    session.flush()
    return {"day": day.date(), "match": match, "coupons": coupons}
