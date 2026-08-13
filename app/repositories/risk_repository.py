"""Persistance des facteurs de risque."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.context import RiskFactor
from app.risk.schemas import RiskFactorItem


class RiskRepository:
    """Sauvegarde et récupère les facteurs de risque."""

    def save_factors(self, match_id: int, factors: list[RiskFactorItem]) -> None:
        """Remplace les facteurs de risque d'un match."""
        self.session.execute(delete(RiskFactor).where(RiskFactor.match_id == match_id))
        for item in factors:
            self.session.add(
                RiskFactor(
                    match_id=match_id,
                    factor=item.factor,
                    impact=item.impact,
                    severity=item.severity,
                )
            )
        self.session.flush()

    def get_factors(self, match_id: int) -> list[RiskFactor]:
        return list(
            self.session.scalars(
                select(RiskFactor).where(RiskFactor.match_id == match_id)
            ).all()
        )

    def __init__(self, session: Session):
        self.session = session
