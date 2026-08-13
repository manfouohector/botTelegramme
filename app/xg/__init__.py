"""xG Engine — estimation xG ou proxy calibré."""

__all__ = [
    "XGEngine",
    "MatchXG",
    "XGEngineError",
    "MatchNotFoundError",
    "InsufficientXGDataError",
]


def __getattr__(name: str):
    if name == "XGEngine":
        from app.xg.xg_engine import XGEngine
        return XGEngine
    if name == "MatchXG":
        from app.xg.schemas import MatchXG
        return MatchXG
    if name == "XGEngineError":
        from app.xg.exceptions import XGEngineError
        return XGEngineError
    if name == "MatchNotFoundError":
        from app.xg.exceptions import MatchNotFoundError
        return MatchNotFoundError
    if name == "InsufficientXGDataError":
        from app.xg.exceptions import InsufficientXGDataError
        return InsufficientXGDataError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
