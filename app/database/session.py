"""Gestion de la connexion PostgreSQL et des sessions SQLAlchemy."""

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import Settings, get_settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine(settings: Settings | None = None) -> Engine:
    """Retourne ou crée le moteur SQLAlchemy."""
    global _engine
    if _engine is not None:
        return _engine

    cfg = settings or get_settings()
    if not cfg.has_database():
        raise RuntimeError(
            "DATABASE_URL non configurée. "
            "Renseignez la variable dans .env avant d'utiliser la base de données."
        )

    _engine = create_engine(
        cfg.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        echo=cfg.app_env == "development" and cfg.log_level == "DEBUG",
    )
    return _engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Retourne la factory de sessions."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    engine = get_engine(settings)
    _session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """Générateur de session pour injection de dépendances (FastAPI, scripts)."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope(settings: Settings | None = None) -> Generator[Session, None, None]:
    """Context manager transactionnel."""
    factory = get_session_factory(settings)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_database_connection(settings: Settings | None = None) -> bool:
    """Vérifie que PostgreSQL est accessible."""
    try:
        engine = get_engine(settings)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("DATABASE_CONNECTION_FAILED | error=%s", exc)
        return False


def reset_engine() -> None:
    """Réinitialise le moteur (utile pour les tests)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def create_engine_from_url(database_url: str, echo: bool = False) -> Engine:
    """Crée un moteur à partir d'une URL (tests)."""
    return create_engine(database_url, echo=echo)
