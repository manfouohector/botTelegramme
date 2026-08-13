"""Évaluation de la confiance — distincte de la probabilité."""

from __future__ import annotations

from app.config.settings import Settings
from app.database.enums import ConfidenceLevel
from app.features.schemas import MatchFeatures
from app.prediction.constants import SELECTION_AWAY, SELECTION_DRAW, SELECTION_HOME
from app.xg.constants import MODEL_UNAVAILABLE
from app.xg.schemas import MatchXG


def assess_confidence(
    features: MatchFeatures,
    xg: MatchXG | None,
    *,
    ml_trained: bool,
    poisson_1x2: dict[str, float],
    ml_1x2: dict[str, float] | None,
    settings: Settings,
) -> ConfidenceLevel:
    """
    Confiance = qualité / cohérence des données, pas la probabilité brute.

    LOW peut entraîner un rejet en publication (Risk Engine, Module 10).
    """
    minimum = settings.prediction_min_matches
    if (
        features.matches_used_home < minimum
        or features.matches_used_away < minimum
    ):
        return ConfidenceLevel.LOW

    if features.data_quality == "LOW":
        return ConfidenceLevel.LOW

    xg_ok = xg is not None and xg.model_type != MODEL_UNAVAILABLE and xg.home_xg is not None

    if ml_trained and ml_1x2:
        disagreement = _max_1x2_disagreement(poisson_1x2, ml_1x2)
        if disagreement > settings.prediction_model_disagreement_threshold:
            return ConfidenceLevel.MEDIUM

    if features.data_quality == "HIGH" and (xg_ok or ml_trained):
        return ConfidenceLevel.HIGH

    if features.data_quality in ("HIGH", "MEDIUM"):
        return ConfidenceLevel.MEDIUM

    return ConfidenceLevel.LOW


def _max_1x2_disagreement(a: dict[str, float], b: dict[str, float]) -> float:
    diffs = []
    for key in (SELECTION_HOME, SELECTION_DRAW, SELECTION_AWAY):
        diffs.append(abs(a.get(key, 0.0) - b.get(key, 0.0)))
    return max(diffs) if diffs else 0.0
