"""Tests unitaires — migrations SQL."""

from pathlib import Path

import pytest

from scripts.run_migrations import (
    MIGRATIONS_DIR,
    _split_sql_statements,
    list_migration_files,
)

EXPECTED_TABLES = {
    "users",
    "subscriptions",
    "payments",
    "competitions",
    "seasons",
    "teams",
    "matches",
    "match_statistics",
    "players",
    "injuries",
    "lineups",
    "markets",
    "odds",
    "ai_models",
    "model_features",
    "predictions",
    "prediction_results",
    "context_factors",
    "risk_factors",
    "coupons",
    "coupon_predictions",
    "coupon_versions",
    "api_usage",
    "system_runs",
    "schema_migrations",
}


class TestMigrationFiles:
    def test_migrations_directory_exists(self):
        assert MIGRATIONS_DIR.exists()

    def test_list_migration_files_sorted(self):
        files = list_migration_files()
        assert len(files) >= 1
        assert files[0].name == "001_init_schema.sql"

    def test_init_schema_contains_all_tables(self):
        sql_path = MIGRATIONS_DIR / "001_init_schema.sql"
        content = sql_path.read_text(encoding="utf-8").lower()
        for table in EXPECTED_TABLES:
            assert f"create table if not exists {table}" in content, f"Table manquante : {table}"

    def test_split_sql_statements(self):
        sql = """
        -- comment
        BEGIN;
        CREATE TABLE foo (id INT);
        CREATE TABLE bar (id INT);
        COMMIT;
        """
        statements = _split_sql_statements(sql)
        assert len(statements) == 2
        assert "CREATE TABLE foo" in statements[0]
        assert "CREATE TABLE bar" in statements[1]

    def test_split_empty_sql(self):
        assert _split_sql_statements("-- only comments\n") == []
