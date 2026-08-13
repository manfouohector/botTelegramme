"""Module génération quotidienne — pipeline admin."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.generation.schemas import (
        DailyStatus,
        GenerationBatchResult,
        HistoryDaySummary,
    )

__all__ = [
    "DailyStatus",
    "GenerationBatchResult",
    "HistoryDaySummary",
]


def __getattr__(name: str):
    if name in __all__:
        from app.generation import schemas

        return getattr(schemas, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
