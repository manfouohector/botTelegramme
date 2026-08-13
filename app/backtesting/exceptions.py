"""Exceptions backtesting."""


class BacktestingError(Exception):
    """Erreur générique backtesting."""


class InsufficientBacktestDataError(BacktestingError):
    """Données historiques insuffisantes."""


class ModelRegistryError(BacktestingError):
    """Erreur model registry."""


class ClvError(BacktestingError):
    """Erreur CLV."""
