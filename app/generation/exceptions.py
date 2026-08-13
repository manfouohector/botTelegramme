"""Exceptions génération pipeline."""


class GenerationError(Exception):
    """Erreur générique génération."""


class GenerationStageError(GenerationError):
    """Échec à une étape précise du pipeline."""

    def __init__(self, stage: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.message = message
