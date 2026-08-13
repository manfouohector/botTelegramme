"""Persistance Model Registry."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.prediction import AIModel


class ModelRegistryRepository:
    """Accès PostgreSQL pour ai_models (registry)."""

    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, model_id: int) -> AIModel | None:
        return self.session.get(AIModel, model_id)

    def list_by_name(self, name: str) -> list[AIModel]:
        return list(
            self.session.scalars(
                select(AIModel)
                .where(AIModel.name == name)
                .order_by(AIModel.trained_at.desc().nullslast(), AIModel.created_at.desc())
            ).all()
        )

    def get_active(self, name: str) -> AIModel | None:
        return self.session.scalar(
            select(AIModel).where(AIModel.name == name, AIModel.active.is_(True)).limit(1)
        )

    def upsert_model(
        self,
        name: str,
        version: str,
        model_type: str,
        *,
        metrics: dict,
        trained_at: datetime | None,
        activate: bool = False,
    ) -> AIModel:
        existing = self.session.scalar(
            select(AIModel).where(AIModel.name == name, AIModel.version == version)
        )
        if existing is not None:
            existing.metrics = metrics
            existing.trained_at = trained_at
            existing.type = model_type
            if activate:
                self._deactivate_siblings(name, keep_id=existing.id)
                existing.active = True
            self.session.flush()
            return existing

        if activate:
            self._deactivate_siblings(name)

        model = AIModel(
            name=name,
            version=version,
            type=model_type,
            metrics=metrics,
            trained_at=trained_at,
            active=activate,
        )
        self.session.add(model)
        self.session.flush()
        return model

    def activate(self, model_id: int) -> AIModel | None:
        model = self.get_by_id(model_id)
        if model is None:
            return None
        self._deactivate_siblings(model.name, keep_id=model_id)
        model.active = True
        self.session.flush()
        return model

    def _deactivate_siblings(self, name: str, *, keep_id: int | None = None) -> None:
        stmt = update(AIModel).where(AIModel.name == name, AIModel.active.is_(True))
        if keep_id is not None:
            stmt = stmt.where(AIModel.id != keep_id)
        self.session.execute(stmt.values(active=False))
        self.session.flush()
