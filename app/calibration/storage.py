"""Persistance des calibrateurs sur disque."""

from __future__ import annotations

import pickle
from dataclasses import dataclass, field
from pathlib import Path

from app.calibration.calibrators import MarketCalibrator
from app.calibration.constants import CALIBRATION_VERSION, DEFAULT_ARTIFACT_DIR


@dataclass
class CalibrationArtifact:
    """État sérialisable des calibrateurs."""

    method: str
    version: str = CALIBRATION_VERSION
    market_calibrators: dict[str, MarketCalibrator] = field(default_factory=dict)


def save_artifact(artifact: CalibrationArtifact, path: str | Path) -> Path:
    """Sauvegarde l'artifact calibration."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        pickle.dump(artifact, handle)
    return target


def load_artifact(path: str | Path) -> CalibrationArtifact:
    """Charge un artifact calibration."""
    with Path(path).open("rb") as handle:
        artifact = pickle.load(handle)
    if not isinstance(artifact, CalibrationArtifact):
        raise ValueError("Fichier calibration invalide")
    return artifact


def default_artifact_path(base_dir: str = DEFAULT_ARTIFACT_DIR) -> Path:
    return Path(base_dir) / "calibrators.pkl"
