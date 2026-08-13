"""Prediction Engine — probabilités football."""

__all__ = [
    "PredictionEngine",
    "MatchPrediction",
    "MarketProbabilities",
    "PredictionEngineError",
    "MatchNotFoundError",
    "InsufficientPredictionDataError",
]


def __getattr__(name: str):
    if name == "PredictionEngine":
        from app.prediction.prediction_engine import PredictionEngine
        return PredictionEngine
    if name in ("MatchPrediction", "MarketProbabilities"):
        from app.prediction.schemas import MatchPrediction, MarketProbabilities
        return MatchPrediction if name == "MatchPrediction" else MarketProbabilities
    if name == "PredictionEngineError":
        from app.prediction.exceptions import PredictionEngineError
        return PredictionEngineError
    if name == "MatchNotFoundError":
        from app.prediction.exceptions import MatchNotFoundError
        return MatchNotFoundError
    if name == "InsufficientPredictionDataError":
        from app.prediction.exceptions import InsufficientPredictionDataError
        return InsufficientPredictionDataError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
