"""Backtesting, Model Registry et CLV."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.backtesting.schemas import (
        BacktestComparisonReport,
        BacktestReport,
        ClvAnalysisReport,
        ModelVersionComparison,
    )

__all__ = [
    "BacktestComparisonReport",
    "BacktestEngine",
    "BacktestReport",
    "ClvAnalysisReport",
    "ClvService",
    "ModelRegistry",
    "ModelVersionComparison",
]


def __getattr__(name: str):
    if name == "BacktestEngine":
        from app.backtesting.backtest_engine import BacktestEngine

        return BacktestEngine
    if name == "ClvService":
        from app.backtesting.clv_service import ClvService

        return ClvService
    if name == "ModelRegistry":
        from app.backtesting.model_registry import ModelRegistry

        return ModelRegistry
    if name in __all__:
        from app.backtesting import schemas

        return getattr(schemas, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
