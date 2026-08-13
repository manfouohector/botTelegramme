"""Feature Engineering — calcul de features pour le Prediction Engine."""

__all__ = [
    "FeatureEngine",
    "MatchFeatures",
    "TeamFormFeatures",
    "FeatureEngineError",
    "MatchNotFoundError",
    "InsufficientDataError",
]


def __getattr__(name: str):
    if name == "FeatureEngine":
        from app.features.feature_engine import FeatureEngine
        return FeatureEngine
    if name in ("MatchFeatures", "TeamFormFeatures"):
        from app.features.schemas import MatchFeatures, TeamFormFeatures
        return MatchFeatures if name == "MatchFeatures" else TeamFormFeatures
    if name == "FeatureEngineError":
        from app.features.exceptions import FeatureEngineError
        return FeatureEngineError
    if name == "MatchNotFoundError":
        from app.features.exceptions import MatchNotFoundError
        return MatchNotFoundError
    if name == "InsufficientDataError":
        from app.features.exceptions import InsufficientDataError
        return InsufficientDataError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
