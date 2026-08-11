"""
app/db/database.py — Connexion SQLAlchemy à PostgreSQL
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise EnvironmentError("DATABASE_URL non définie dans les variables d'environnement")

# Adapter l'URL pour SQLAlchemy (postgres:// → postgresql://)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,          # Vérifie la connexion avant chaque usage
    pool_recycle=300,            # Recycle les connexions toutes les 5 minutes
    connect_args={"sslmode": "require"},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles SQLAlchemy"""
    pass


def get_db():
    """
    Générateur de session DB à utiliser dans les dépendances FastAPI.
    Usage : db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Erreur de session DB: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def test_connection() -> bool:
    """Teste la connexion à la base de données. Retourne True si OK."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Connexion PostgreSQL (SQLAlchemy) établie avec succès")
        return True
    except Exception as e:
        logger.error(f"❌ Échec de la connexion PostgreSQL: {e}")
        return False
