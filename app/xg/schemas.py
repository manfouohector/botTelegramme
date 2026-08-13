"""Schémas xG."""

from dataclasses import dataclass, field


@dataclass
class ShotStats:
    """Statistiques de tirs extraites d'un match."""

    shots: float | None = None
    shots_on_target: float | None = None

    @property
    def has_data(self) -> bool:
        return self.shots is not None or self.shots_on_target is not None


@dataclass
class XGModelMetrics:
    """Métriques d'évaluation du modèle proxy."""

    sample_size: int = 0
    mean_absolute_error: float | None = None
    poisson_deviance: float | None = None

    def to_dict(self) -> dict:
        return {
            "sample_size": self.sample_size,
            "mean_absolute_error": self.mean_absolute_error,
            "poisson_deviance": self.poisson_deviance,
        }


@dataclass
class MatchXG:
    """Estimation xG pour un match."""

    match_id: int
    external_match_id: int
    home_xg: float | None
    away_xg: float | None
    xg_difference: float | None
    home_xg_form: float | None
    away_xg_form: float | None
    model_type: str
    model_version: str
    data_quality: str = "LOW"
    is_true_xg: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "match_id": self.match_id,
            "external_match_id": self.external_match_id,
            "home_xg": round(self.home_xg, 4) if self.home_xg is not None else None,
            "away_xg": round(self.away_xg, 4) if self.away_xg is not None else None,
            "xg_difference": round(self.xg_difference, 4) if self.xg_difference is not None else None,
            "home_xg_form": round(self.home_xg_form, 4) if self.home_xg_form is not None else None,
            "away_xg_form": round(self.away_xg_form, 4) if self.away_xg_form is not None else None,
            "model_type": self.model_type,
            "model_version": self.model_version,
            "data_quality": self.data_quality,
            "is_true_xg": self.is_true_xg,
            "metadata": self.metadata,
        }

    def flat_features(self) -> dict[str, float]:
        """Features xG pour ML — None exclu."""
        flat: dict[str, float] = {}
        mapping = {
            "home_xg": self.home_xg,
            "away_xg": self.away_xg,
            "xg_difference": self.xg_difference,
            "home_xg_form": self.home_xg_form,
            "away_xg_form": self.away_xg_form,
        }
        for key, val in mapping.items():
            if val is not None:
                flat[key] = round(val, 4)
        return flat
