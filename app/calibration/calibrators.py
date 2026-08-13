"""Calibrateurs Platt et Isotonic."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from app.calibration.constants import CALIBRATOR_ISOTONIC, CALIBRATOR_PLATT
from app.calibration.exceptions import CalibratorNotFittedError
from app.prediction.markets import _normalize


@dataclass
class BinaryCalibrator:
    """Calibre une probabilité binaire via Platt ou Isotonic."""

    method: str
    _model: LogisticRegression | IsotonicRegression | None = None
    fitted: bool = False
    sample_size: int = 0

    def fit(self, probabilities: list[float], outcomes: list[int]) -> bool:
        if len(probabilities) < 5 or len(set(outcomes)) < 2:
            self.fitted = False
            self.sample_size = len(probabilities)
            return False

        probs = np.clip(np.array(probabilities, dtype=float), 1e-6, 1.0 - 1e-6)
        y = np.array(outcomes, dtype=int)

        if self.method == CALIBRATOR_PLATT:
            self._model = LogisticRegression(max_iter=1000, solver="lbfgs")
            self._model.fit(probs.reshape(-1, 1), y)
        elif self.method == CALIBRATOR_ISOTONIC:
            self._model = IsotonicRegression(out_of_bounds="clip")
            self._model.fit(probs, y)
        else:
            return False

        self.fitted = True
        self.sample_size = len(probabilities)
        return True

    def calibrate(self, probability: float) -> float:
        if not self.fitted or self._model is None:
            raise CalibratorNotFittedError(f"Calibrateur {self.method} non entraîné")

        prob = float(np.clip(probability, 1e-6, 1.0 - 1e-6))
        if self.method == CALIBRATOR_PLATT:
            assert isinstance(self._model, LogisticRegression)
            return float(self._model.predict_proba(np.array([[prob]]))[0][1])
        assert isinstance(self._model, IsotonicRegression)
        return float(self._model.predict(np.array([prob]))[0])


@dataclass
class MarketCalibrator:
    """Calibre toutes les issues d'un marché puis renormalise."""

    market_code: str
    method: str
    selection_calibrators: dict[str, BinaryCalibrator] = field(default_factory=dict)
    fitted: bool = False

    def fit(
        self,
        records: list,
        selections: tuple[str, ...],
    ) -> bool:
        any_fitted = False
        for selection in selections:
            calibrator = BinaryCalibrator(method=self.method)
            probs = [r.probabilities[selection] for r in records if selection in r.probabilities]
            outcomes = [
                1 if r.actual_selection == selection else 0
                for r in records
                if selection in r.probabilities
            ]
            if calibrator.fit(probs, outcomes):
                any_fitted = True
            self.selection_calibrators[selection] = calibrator

        self.fitted = any_fitted
        return self.fitted

    def calibrate(self, probabilities: dict[str, float]) -> dict[str, float]:
        if not self.fitted:
            return dict(probabilities)

        calibrated: dict[str, float] = {}
        for selection, prob in probabilities.items():
            calibrator = self.selection_calibrators.get(selection)
            if calibrator is None or not calibrator.fitted:
                calibrated[selection] = prob
            else:
                calibrated[selection] = calibrator.calibrate(prob)
        return _normalize(calibrated)
