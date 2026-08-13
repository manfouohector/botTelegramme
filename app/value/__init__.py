"""Value Engine — comparaison modèle vs cotes bookmakers."""

__all__ = [
    "ValueEngine",
    "OddsCollector",
    "OddsAPIClient",
    "MatchValueAnalysis",
    "ValueOpportunity",
    "ValueEngineError",
    "OddsNotFoundError",
]


def __getattr__(name: str):
    if name == "ValueEngine":
        from app.value.value_engine import ValueEngine
        return ValueEngine
    if name == "OddsCollector":
        from app.value.odds_collector import OddsCollector
        return OddsCollector
    if name == "OddsAPIClient":
        from app.value.odds_api_client import OddsAPIClient
        return OddsAPIClient
    if name == "MatchValueAnalysis":
        from app.value.schemas import MatchValueAnalysis
        return MatchValueAnalysis
    if name == "ValueOpportunity":
        from app.value.schemas import ValueOpportunity
        return ValueOpportunity
    if name == "ValueEngineError":
        from app.value.exceptions import ValueEngineError
        return ValueEngineError
    if name == "OddsNotFoundError":
        from app.value.exceptions import OddsNotFoundError
        return OddsNotFoundError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
