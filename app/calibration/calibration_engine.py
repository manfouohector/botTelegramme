"""Calibration Engine — ajustement Platt / Isotonic + évaluation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.calibration.calibrators import MarketCalibrator
from app.calibration.constants import (
    CALIBRATOR_ISOTONIC,
    CALIBRATOR_NONE,
    CALIBRATOR_PLATT,
    CALIBRATION_VERSION,
)
from app.calibration.evaluator import MARKET_SELECTIONS, PredictionEvaluator
from app.calibration.exceptions import InsufficientCalibrationDataError
from app.calibration.metrics import evaluate_market
from app.calibration.schemas import (
    CalibratedMatchPrediction,
    EvaluationReport,
    MarketEvaluationRecord,
)
from app.calibration.storage import (
    CalibrationArtifact,
    default_artifact_path,
    load_artifact,
    save_artifact,
)
from app.config.settings import Settings, get_settings
from app.prediction.prediction_engine import PredictionEngine
from app.prediction.schemas import MarketProbabilities, MatchPrediction
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)


class CalibrationEngine:
    """
    Calibre les probabilités du Prediction Engine.

    Méthodes : Platt Scaling, Isotonic Regression (par issue, renormalisation).
    """

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        *,
        prediction_engine: PredictionEngine | None = None,
    ):
        self.session = session
        self.settings = settings or get_settings()
        self.prediction_engine = prediction_engine or PredictionEngine(session, self.settings)
        self.evaluator = PredictionEvaluator(session, self.prediction_engine)
        self.market_calibrators: dict[str, MarketCalibrator] = {}
        self.method: str = self.settings.calibration_method.upper()
        self.fitted = False

    @property
    def is_enabled(self) -> bool:
        return self.settings.calibration_enable and self.method != CALIBRATOR_NONE

    def fit(self, records: list[MarketEvaluationRecord]) -> bool:
        """Entraîne les calibrateurs par marché."""
        if not self.is_enabled:
            return False

        if len(records) < self.settings.calibration_min_samples:
            raise InsufficientCalibrationDataError(
                f"Échantillons insuffisants ({len(records)}/{self.settings.calibration_min_samples})"
            )

        self.market_calibrators.clear()
        any_fitted = False

        for market_code, selections in MARKET_SELECTIONS.items():
            market_records = [r for r in records if r.market_code == market_code]
            if len(market_records) < self.settings.calibration_min_samples // 3:
                continue

            calibrator = MarketCalibrator(market_code=market_code, method=self.method)
            if calibrator.fit(market_records, selections):
                self.market_calibrators[market_code] = calibrator
                any_fitted = True

        self.fitted = any_fitted
        log_event(
            logger,
            "CALIBRATION_FITTED",
            method=self.method,
            markets=list(self.market_calibrators.keys()),
            sample_size=len(records),
        )
        return self.fitted

    def fit_from_season(
        self,
        season_id: int,
        before_date: datetime,
        *,
        competition_id: int | None = None,
        limit: int | None = None,
    ) -> bool:
        """Collecte l'historique et entraîne les calibrateurs."""
        records = self.evaluator.collect_season_records(
            season_id,
            before_date,
            competition_id=competition_id,
            limit=limit,
        )
        return self.fit(records)

    def calibrate(self, prediction: MatchPrediction) -> CalibratedMatchPrediction:
        """Applique la calibration à une prédiction."""
        calibrated_markets: list[MarketProbabilities] = []

        for market in prediction.markets:
            calibrator = self.market_calibrators.get(market.market_code)
            if calibrator is None or not calibrator.fitted or not self.fitted:
                calibrated_markets.append(
                    MarketProbabilities(
                        market_code=market.market_code,
                        probabilities=dict(market.probabilities),
                        model_type=market.model_type,
                    )
                )
                continue

            probs = calibrator.calibrate(market.probabilities)
            calibrated_markets.append(
                MarketProbabilities(
                    market_code=market.market_code,
                    probabilities=probs,
                    model_type=f"{market.model_type}_CALIBRATED",
                )
            )

        return CalibratedMatchPrediction(
            raw=prediction,
            markets=calibrated_markets,
            calibration_method=self.method if self.fitted else CALIBRATOR_NONE,
            calibration_version=CALIBRATION_VERSION,
            metadata={"calibration_applied": self.fitted},
        )

    def evaluate(
        self,
        records: list[MarketEvaluationRecord],
    ) -> EvaluationReport:
        """Évalue métriques brutes et calibrées."""
        market_codes = sorted({r.market_code for r in records})
        raw_metrics = {
            code: evaluate_market(records, code, n_bins=self.settings.calibration_bins)
            for code in market_codes
        }

        calibrated_metrics = None
        if self.fitted:
            calibrated_records = self._apply_calibration_to_records(records)
            calibrated_metrics = {
                code: evaluate_market(
                    calibrated_records, code, n_bins=self.settings.calibration_bins
                )
                for code in market_codes
            }

        return EvaluationReport(
            sample_size=len(records),
            method=self.method,
            raw_metrics=raw_metrics,
            calibrated_metrics=calibrated_metrics,
        )

    def evaluate_season(
        self,
        season_id: int,
        before_date: datetime,
        *,
        competition_id: int | None = None,
        limit: int | None = None,
    ) -> EvaluationReport:
        """Collecte et évalue sur une saison."""
        records = self.evaluator.collect_season_records(
            season_id,
            before_date,
            competition_id=competition_id,
            limit=limit,
        )
        return self.evaluate(records)

    def save(self, path: str | Path | None = None) -> Path:
        """Persiste les calibrateurs."""
        target = Path(path) if path else default_artifact_path(self.settings.calibration_artifact_dir)
        artifact = CalibrationArtifact(
            method=self.method,
            market_calibrators=self.market_calibrators,
        )
        saved = save_artifact(artifact, target)
        log_event(logger, "CALIBRATION_SAVED", path=str(saved))
        return saved

    def load(self, path: str | Path | None = None) -> bool:
        """Charge des calibrateurs depuis le disque."""
        target = Path(path) if path else default_artifact_path(self.settings.calibration_artifact_dir)
        if not target.exists():
            return False
        artifact = load_artifact(target)
        self.method = artifact.method
        self.market_calibrators = artifact.market_calibrators
        self.fitted = any(c.fitted for c in self.market_calibrators.values())
        log_event(logger, "CALIBRATION_LOADED", path=str(target), fitted=self.fitted)
        return self.fitted

    def _apply_calibration_to_records(
        self,
        records: list[MarketEvaluationRecord],
    ) -> list[MarketEvaluationRecord]:
        calibrated: list[MarketEvaluationRecord] = []
        for record in records:
            calibrator = self.market_calibrators.get(record.market_code)
            if calibrator is None or not calibrator.fitted:
                calibrated.append(record)
                continue
            calibrated.append(
                MarketEvaluationRecord(
                    match_id=record.match_id,
                    market_code=record.market_code,
                    probabilities=calibrator.calibrate(record.probabilities),
                    actual_selection=record.actual_selection,
                )
            )
        return calibrated
