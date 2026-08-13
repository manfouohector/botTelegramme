"""Exécution des migrations SQL PostgreSQL."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import get_settings
from app.database.session import get_engine, reset_engine
from app.utils.logging import get_logger, log_event

logger = get_logger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
MIGRATION_PATTERN = re.compile(r"^(\d+)_.+\.sql$")


@dataclass
class MigrationResult:
    filename: str
    applied: bool
    skipped: bool = False
    error: str | None = None


def list_migration_files(migrations_dir: Path | None = None) -> list[Path]:
    """Liste les fichiers de migration triés par numéro."""
    directory = migrations_dir or MIGRATIONS_DIR
    if not directory.exists():
        return []

    files = []
    for path in directory.glob("*.sql"):
        match = MIGRATION_PATTERN.match(path.name)
        if match:
            files.append((int(match.group(1)), path))
    return [path for _, path in sorted(files, key=lambda item: item[0])]


def ensure_migrations_table(engine: Engine) -> None:
    """Crée la table de suivi des migrations si absente."""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    id SERIAL PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )
                """
            )
        )


def get_applied_migrations(engine: Engine) -> set[str]:
    """Retourne l'ensemble des migrations déjà appliquées."""
    ensure_migrations_table(engine)
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT filename FROM schema_migrations")).fetchall()
    return {row[0] for row in rows}


def _split_sql_statements(sql_content: str) -> list[str]:
    """Découpe un fichier SQL en statements exécutables."""
    statements: list[str] = []
    buffer: list[str] = []

    for line in sql_content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        if stripped.upper() in {"BEGIN", "BEGIN;", "COMMIT", "COMMIT;"}:
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []

    if buffer:
        statement = "\n".join(buffer).strip()
        if statement:
            statements.append(statement)

    return statements


def apply_migration(engine: Engine, migration_path: Path) -> None:
    """Applique un fichier SQL de migration."""
    sql_content = migration_path.read_text(encoding="utf-8")
    statements = _split_sql_statements(sql_content)

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
        conn.execute(
            text(
                "INSERT INTO schema_migrations (filename, applied_at) "
                "VALUES (:filename, :applied_at) "
                "ON CONFLICT (filename) DO NOTHING"
            ),
            {
                "filename": migration_path.name,
                "applied_at": datetime.now(timezone.utc),
            },
        )


def run_migrations(engine: Engine | None = None) -> list[MigrationResult]:
    """Applique toutes les migrations en attente."""
    eng = engine or get_engine()
    results: list[MigrationResult] = []
    applied = get_applied_migrations(eng)
    pending = [f for f in list_migration_files() if f.name not in applied]

    log_event(logger, "MIGRATIONS_STARTED", pending_count=len(pending))

    for migration_path in pending:
        try:
            apply_migration(eng, migration_path)
            log_event(logger, "MIGRATION_APPLIED", filename=migration_path.name)
            results.append(MigrationResult(filename=migration_path.name, applied=True))
        except SQLAlchemyError as exc:
            log_event(
                logger,
                "MIGRATION_FAILED",
                level="ERROR",
                filename=migration_path.name,
                error=str(exc),
            )
            results.append(
                MigrationResult(filename=migration_path.name, applied=False, error=str(exc))
            )
            break

    skipped = [
        MigrationResult(filename=f.name, applied=False, skipped=True)
        for f in list_migration_files()
        if f.name in applied
    ]
    results.extend(skipped)

    log_event(
        logger,
        "MIGRATIONS_COMPLETED",
        applied=sum(1 for r in results if r.applied),
        skipped=sum(1 for r in results if r.skipped),
    )
    return results


def main() -> int:
    """Point d'entrée CLI pour lancer les migrations."""
    settings = get_settings()
    if not settings.has_database():
        logger.error("DATABASE_URL manquante — impossible d'exécuter les migrations.")
        return 1

    try:
        results = run_migrations()
    except Exception as exc:
        logger.error("MIGRATIONS_FATAL_ERROR | error=%s", exc)
        return 1
    finally:
        reset_engine()

    if any(r.error for r in results):
        return 1
    print(f"Migrations terminées : {sum(1 for r in results if r.applied)} appliquée(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
