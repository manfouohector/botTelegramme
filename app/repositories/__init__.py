"""Repositories — accès PostgreSQL."""

__all__ = [
    "FootballRepository",
    "ApiUsageRepository",
    "MatchHistoryRepository",
    "ContextRepository",
    "TeamMatchRecord",
]


def __getattr__(name: str):
    if name == "FootballRepository":
        from app.repositories.football_repository import FootballRepository
        return FootballRepository
    if name == "ApiUsageRepository":
        from app.repositories.api_usage_repository import ApiUsageRepository
        return ApiUsageRepository
    if name == "MatchHistoryRepository":
        from app.repositories.match_history_repository import MatchHistoryRepository
        return MatchHistoryRepository
    if name == "TeamMatchRecord":
        from app.features.records import TeamMatchRecord
        return TeamMatchRecord
    if name == "ContextRepository":
        from app.repositories.context_repository import ContextRepository
        return ContextRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
