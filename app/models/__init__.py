"""Modèles SQLAlchemy — enregistrement centralisé."""

from app.models.context import ContextFactor, RiskFactor
from app.models.coupon import Coupon, CouponPrediction, CouponVersion
from app.models.football import Competition, Season, Team
from app.models.market import Market, Odd
from app.models.match import Match, MatchStatistic
from app.models.payment import Payment
from app.models.player import Injury, Lineup, Player
from app.models.prediction import AIModel, ModelFeature, Prediction, PredictionResult
from app.models.subscription import Subscription
from app.models.system import ApiUsage, SystemRun
from app.models.user import User

__all__ = [
    "User",
    "Subscription",
    "Payment",
    "Competition",
    "Season",
    "Team",
    "Match",
    "MatchStatistic",
    "Player",
    "Injury",
    "Lineup",
    "Market",
    "Odd",
    "AIModel",
    "ModelFeature",
    "Prediction",
    "PredictionResult",
    "ContextFactor",
    "RiskFactor",
    "Coupon",
    "CouponPrediction",
    "CouponVersion",
    "ApiUsage",
    "SystemRun",
]
