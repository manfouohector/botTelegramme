"""Modèle proxy xG basé sur tirs — Poisson calibré sur données historiques."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import PoissonRegressor

from app.features.records import TeamMatchRecord
from app.xg.constants import PROXY_MODEL_VERSION
from app.xg.schemas import ShotStats, XGModelMetrics
from app.xg.shot_stats import extract_shot_stats


@dataclass
class TrainingSample:
    shots: float
    shots_on_target: float
    is_home: float
    goals: int


@dataclass
class ShotProxyModel:
    """Régression Poisson : tirs → buts attendus (proxy xG, pas xG opta)."""

    regressor: PoissonRegressor | None = None
    version: str = PROXY_MODEL_VERSION
    trained: bool = False
    sample_size: int = 0

    def fit(self, samples: list[TrainingSample]) -> XGModelMetrics:
        if len(samples) < 5:
            self.trained = False
            self.sample_size = len(samples)
            return XGModelMetrics(sample_size=len(samples))

        x = np.array([
            [s.shots, s.shots_on_target, s.is_home]
            for s in samples
        ])
        y = np.array([s.goals for s in samples])

        self.regressor = PoissonRegressor(alpha=0.1, max_iter=500)
        self.regressor.fit(x, y)
        self.trained = True
        self.sample_size = len(samples)

        preds = self.regressor.predict(x)
        mae = float(np.mean(np.abs(y - preds)))
        deviance = _poisson_deviance(y, preds)

        return XGModelMetrics(
            sample_size=len(samples),
            mean_absolute_error=round(mae, 4),
            poisson_deviance=round(deviance, 4),
        )

    def predict(self, shot_stats: ShotStats, *, is_home: bool) -> float | None:
        if not self.trained or self.regressor is None:
            return None
        if shot_stats.shots is None and shot_stats.shots_on_target is None:
            return None

        shots = shot_stats.shots if shot_stats.shots is not None else 0.0
        sot = shot_stats.shots_on_target if shot_stats.shots_on_target is not None else 0.0
        x = np.array([[shots, sot, 1.0 if is_home else 0.0]])
        pred = float(self.regressor.predict(x)[0])
        return max(0.0, pred)


def build_training_samples(records: list[TeamMatchRecord]) -> list[TrainingSample]:
    """Construit les échantillons d'entraînement depuis l'historique."""
    samples: list[TrainingSample] = []
    for rec in records:
        ss = extract_shot_stats(rec.stats)
        if ss.shots is None and ss.shots_on_target is None:
            continue
        samples.append(
            TrainingSample(
                shots=ss.shots or 0.0,
                shots_on_target=ss.shots_on_target or 0.0,
                is_home=1.0 if rec.is_home else 0.0,
                goals=rec.goals_scored,
            )
        )
    return samples


def _poisson_deviance(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    eps = 1e-9
    y_pred = np.clip(y_pred, eps, None)
    y_true = np.clip(y_true, eps, None)
    return float(2 * np.mean(y_true * np.log(y_true / y_pred) - (y_true - y_pred)))
