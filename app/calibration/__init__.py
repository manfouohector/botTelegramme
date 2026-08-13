"""Calibration — ajustement des probabilités."""

__all__ = [
    "CalibrationEngine",
    "CalibratedMatchPrediction",
    "EvaluationReport",
    "MarketMetrics",
    "CalibrationError",
    "CalibratorNotFittedError",
    "InsufficientCalibrationDataError",
]


def __getattr__(name: str):
    if name == "CalibrationEngine":
        from app.calibration.calibration_engine import CalibrationEngine
        return CalibrationEngine
    if name == "CalibratedMatchPrediction":
        from app.calibration.schemas import CalibratedMatchPrediction
        return CalibratedMatchPrediction
    if name == "EvaluationReport":
        from app.calibration.schemas import EvaluationReport
        return EvaluationReport
    if name == "MarketMetrics":
        from app.calibration.schemas import MarketMetrics
        return MarketMetrics
    if name == "CalibrationError":
        from app.calibration.exceptions import CalibrationError
        return CalibrationError
    if name == "CalibratorNotFittedError":
        from app.calibration.exceptions import CalibratorNotFittedError
        return CalibratorNotFittedError
    if name == "InsufficientCalibrationDataError":
        from app.calibration.exceptions import InsufficientCalibrationDataError
        return InsufficientCalibrationDataError
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
