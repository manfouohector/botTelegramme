"""Exceptions calibration."""


class CalibrationError(Exception):
    """Erreur générique calibration."""


class CalibratorNotFittedError(CalibrationError):
    """Calibrateur non entraîné."""


class InsufficientCalibrationDataError(CalibrationError):
    """Échantillons insuffisants pour calibrer."""
