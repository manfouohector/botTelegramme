"""Fixtures pytest pour les tests base de données."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.database.session import reset_engine
import app.models  # noqa: F401 — enregistre tous les modèles


@pytest.fixture
def db_engine():
    """Moteur SQLite en mémoire pour tests unitaires."""
    reset_engine()
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()
    reset_engine()


@pytest.fixture
def db_session(db_engine) -> Session:
    """Session SQLAlchemy — rollback automatique en fin de test."""
    factory = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
