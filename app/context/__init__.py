"""Context Engine — calcul du contexte match structuré."""

__all__ = [
    "ContextEngine",
    "MatchContext",
    "TeamStanding",
    "ContextFactorValue",
    "ContextEngineError",
    "MatchNotFoundError",
    "InsufficientStandingsError",
]


def __getattr__(name: str):
    if name == "ContextEngine":
        from app.context.context_engine import ContextEngine
        return ContextEngine
    if name in ("MatchContext", "TeamStanding", "ContextFactorValue"):
        from app.context.schemas import ContextFactorValue, MatchContext, TeamStanding
        return {"MatchContext": MatchContext, "TeamStanding": TeamStanding, "ContextFactorValue": ContextFactorValue}[name]
    if name == "ContextEngineError":
        from app.context.exceptions import ContextEngineError
        return ContextEngineError
    if name == "MatchNotFoundError":
        from app.context.exceptions import MatchNotFoundError
        return MatchNotFoundError
    if name == "InsufficientStandingsError":
        from app.context.exceptions import InsufficientStandingsError
        return InsufficientStandingsError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
