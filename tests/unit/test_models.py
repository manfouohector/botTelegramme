"""Tests unitaires — modèles SQLAlchemy."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.database.enums import (
    CouponStatus,
    CouponType,
    DataStatus,
    MatchStatus,
    PaymentMethod,
    PaymentStatus,
    SubscriptionStatus,
    SystemRunStatus,
)
from app.models import (
    AIModel,
    ApiUsage,
    Competition,
    ContextFactor,
    Coupon,
    CouponPrediction,
    Market,
    Match,
    Payment,
    Prediction,
    Season,
    Subscription,
    SystemRun,
    Team,
    User,
)


class TestUserModel:
    def test_create_user(self, db_session):
        user = User(telegram_id=123456789, username="testuser", first_name="Test")
        db_session.add(user)
        db_session.flush()
        assert user.id is not None
        assert user.telegram_id == 123456789

    def test_unique_telegram_id(self, db_session):
        db_session.add(User(telegram_id=111))
        db_session.add(User(telegram_id=111))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


class TestSubscriptionModel:
    def test_create_subscription(self, db_session):
        user = User(telegram_id=222)
        db_session.add(user)
        db_session.flush()

        now = datetime.now(timezone.utc)
        sub = Subscription(
            user_id=user.id,
            plan="premium",
            date_debut=now,
            date_fin=now + timedelta(days=30),
            statut=SubscriptionStatus.ACTIVE,
        )
        db_session.add(sub)
        db_session.flush()
        assert sub.statut == SubscriptionStatus.ACTIVE


class TestPaymentModel:
    def test_create_payment(self, db_session):
        user = User(telegram_id=333)
        db_session.add(user)
        db_session.flush()

        payment = Payment(
            user_id=user.id,
            amount=Decimal("5000.00"),
            currency="XAF",
            method=PaymentMethod.MANUEL_WHATSAPP,
            payment_status=PaymentStatus.SUCCESS,
        )
        db_session.add(payment)
        db_session.flush()
        assert payment.payment_status == PaymentStatus.SUCCESS


class TestMatchModel:
    @pytest.fixture
    def match_setup(self, db_session):
        comp = Competition(external_id=8, name="Ligue 1", country="France")
        db_session.add(comp)
        db_session.flush()
        season = Season(competition_id=comp.id, external_id=2025, name="2025/2026", is_current=True)
        db_session.add(season)
        db_session.flush()
        home = Team(external_id=100, name="PSG")
        away = Team(external_id=101, name="OM")
        db_session.add_all([home, away])
        db_session.flush()
        return comp, season, home, away

    def test_create_match(self, db_session, match_setup):
        comp, season, home, away = match_setup
        match = Match(
            external_match_id=999001,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=datetime.now(timezone.utc),
            status=MatchStatus.SCHEDULED,
            data_status=DataStatus.MISSING,
        )
        db_session.add(match)
        db_session.flush()
        assert match.external_match_id == 999001

    def test_unique_external_match_id(self, db_session, match_setup):
        comp, season, home, away = match_setup
        scheduled = datetime.now(timezone.utc)
        db_session.add(
            Match(
                external_match_id=999002,
                competition_id=comp.id,
                season_id=season.id,
                home_team_id=home.id,
                away_team_id=away.id,
                scheduled_at=scheduled,
            )
        )
        db_session.add(
            Match(
                external_match_id=999002,
                competition_id=comp.id,
                season_id=season.id,
                home_team_id=home.id,
                away_team_id=away.id,
                scheduled_at=scheduled,
            )
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()


class TestPredictionPipeline:
    @pytest.fixture
    def prediction_setup(self, db_session):
        comp = Competition(external_id=8, name="Ligue 1")
        db_session.add(comp)
        db_session.flush()
        season = Season(competition_id=comp.id, external_id=2025, name="2025/2026")
        db_session.add(season)
        db_session.flush()
        home = Team(external_id=100, name="PSG")
        away = Team(external_id=101, name="OM")
        db_session.add_all([home, away])
        db_session.flush()
        match = Match(
            external_match_id=888001,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=datetime.now(timezone.utc),
        )
        db_session.add(match)
        db_session.flush()
        market = Market(code="1X2", name="Résultat final", active=True)
        db_session.add(market)
        db_session.flush()
        model = AIModel(name="poisson", version="v1.0", type="statistical", active=True)
        db_session.add(model)
        db_session.flush()
        return match, market, model

    def test_create_prediction(self, db_session, prediction_setup):
        match, market, model = prediction_setup
        pred = Prediction(
            match_id=match.id,
            market_id=market.id,
            model_id=model.id,
            model_version="v1.0",
            selection="HOME",
            probability=Decimal("0.680000"),
            value_edge=Decimal("0.091800"),
        )
        db_session.add(pred)
        db_session.flush()
        assert pred.probability == Decimal("0.680000")

    def test_coupon_with_predictions(self, db_session, prediction_setup):
        match, market, model = prediction_setup
        pred = Prediction(
            match_id=match.id,
            market_id=market.id,
            model_id=model.id,
            model_version="v1.0",
            selection="HOME",
            probability=Decimal("0.680000"),
        )
        db_session.add(pred)
        db_session.flush()

        coupon = Coupon(type=CouponType.FREE, status=CouponStatus.PUBLISHED, version=1)
        db_session.add(coupon)
        db_session.flush()

        link = CouponPrediction(coupon_id=coupon.id, prediction_id=pred.id, position=1)
        db_session.add(link)
        db_session.flush()
        assert len(coupon.predictions) == 1


class TestSystemModels:
    def test_api_usage_unique_provider_date(self, db_session):
        from datetime import date

        db_session.add(ApiUsage(provider="sportmonks", date=date(2026, 8, 13), request_count=10))
        db_session.add(ApiUsage(provider="sportmonks", date=date(2026, 8, 13), request_count=20))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_system_run(self, db_session):
        run = SystemRun(
            run_type="daily_analysis",
            status=SystemRunStatus.SUCCESS,
            matches_processed=18,
            predictions_created=42,
            coupons_created=1,
        )
        db_session.add(run)
        db_session.flush()
        assert run.matches_processed == 18


class TestContextFactor:
    def test_context_factor(self, db_session):
        comp = Competition(external_id=1, name="Test League")
        db_session.add(comp)
        db_session.flush()
        season = Season(competition_id=comp.id, external_id=1, name="2025")
        db_session.add(season)
        db_session.flush()
        home = Team(external_id=1, name="Home")
        away = Team(external_id=2, name="Away")
        db_session.add_all([home, away])
        db_session.flush()
        match = Match(
            external_match_id=1,
            competition_id=comp.id,
            season_id=season.id,
            home_team_id=home.id,
            away_team_id=away.id,
            scheduled_at=datetime.now(timezone.utc),
        )
        db_session.add(match)
        db_session.flush()

        factor = ContextFactor(match_id=match.id, factor_name="title_race", value=Decimal("1"))
        db_session.add(factor)
        db_session.flush()
        assert factor.factor_name == "title_race"
