"""Repository — persistance des facteurs de contexte."""

from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.context.schemas import ContextFactorValue, MatchContext
from app.database.enums import InfoReliability
from app.models.context import ContextFactor


class ContextRepository:
    """Sauvegarde et récupère les facteurs de contexte en PostgreSQL."""

    SOURCE_COMPUTED = "context_engine"

    def __init__(self, session: Session):
        self.session = session

    def save_context(self, context: MatchContext) -> None:
        """Remplace les facteurs de contexte d'un match."""
        self.session.execute(
            delete(ContextFactor).where(ContextFactor.match_id == context.match_id)
        )
        for factor in context.factors:
            self.session.add(
                ContextFactor(
                    match_id=context.match_id,
                    factor_name=factor.name,
                    value=Decimal(str(round(factor.value, 4))),
                    source=factor.source or self.SOURCE_COMPUTED,
                    reliability=InfoReliability(factor.reliability),
                )
            )
        self.session.flush()

    def get_factors(self, match_id: int) -> list[ContextFactor]:
        return list(
            self.session.scalars(
                select(ContextFactor)
                .where(ContextFactor.match_id == match_id)
                .order_by(ContextFactor.factor_name)
            ).all()
        )

    def load_as_context_factor_values(self, match_id: int) -> list[ContextFactorValue]:
        rows = self.get_factors(match_id)
        return [
            ContextFactorValue(
                name=row.factor_name,
                value=float(row.value),
                source=row.source or self.SOURCE_COMPUTED,
                reliability=row.reliability.value if hasattr(row.reliability, "value") else str(row.reliability),
            )
            for row in rows
        ]
