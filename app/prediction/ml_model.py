"""Modèle ML 1X2 — régression logistique multinomiale."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from app.prediction.constants import SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME

OUTCOME_LABELS = (SELECTION_HOME, SELECTION_DRAW, SELECTION_AWAY)


@dataclass
class OutcomeMLModel:
    """Prédiction 1X2 via scikit-learn."""

    model: LogisticRegression | None = None
    scaler: StandardScaler | None = None
    feature_names: list[str] = field(default_factory=list)
    trained: bool = False
    sample_size: int = 0

    def fit(self, feature_rows: list[dict[str, float | int | bool]], labels: list[str]) -> bool:
        if len(feature_rows) < 5 or len(set(labels)) < 2:
            self.trained = False
            self.sample_size = len(feature_rows)
            return False

        self.feature_names = sorted({key for row in feature_rows for key in row})
        x = np.array([[float(row.get(name, 0.0)) for name in self.feature_names] for row in feature_rows])
        y = np.array(labels)

        self.scaler = StandardScaler()
        x_scaled = self.scaler.fit_transform(x)

        self.model = LogisticRegression(max_iter=1000, solver="lbfgs")
        self.model.fit(x_scaled, y)
        self.trained = True
        self.sample_size = len(feature_rows)
        return True

    def predict_proba(self, features: dict[str, float | int | bool]) -> dict[str, float] | None:
        if not self.trained or self.model is None or self.scaler is None:
            return None

        x = np.array([[float(features.get(name, 0.0)) for name in self.feature_names]])
        x_scaled = self.scaler.transform(x)
        probs = self.model.predict_proba(x_scaled)[0]
        classes = list(self.model.classes_)
        return {label: float(probs[classes.index(label)]) for label in OUTCOME_LABELS if label in classes}
