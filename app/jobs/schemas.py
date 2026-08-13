"""Schémas résultats jobs planifiés."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class JobResult:
    """Résultat d'exécution d'un job."""

    job_name: str
    success: bool = True
    skipped: bool = False
    reason: str | None = None
    system_run_id: int | None = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "success": self.success,
            "skipped": self.skipped,
            "reason": self.reason,
            "system_run_id": self.system_run_id,
            "details": self.details,
        }
