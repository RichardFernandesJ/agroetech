"""Garante que a migração inicial acompanha os models.

Sem este teste, uma alteração de model sem revisão do Alembic passaria
despercebida até o deploy. O teste roda a migração em um SQLite temporário e
compara o schema resultante com o metadata do SQLAlchemy.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

import app.models  # noqa: F401  (registra todos os models no metadata)
from app.models.base import Base

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_initial_migration_matches_models(tmp_path: Path) -> None:
    database_path = tmp_path / "migrations.db"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    config = _alembic_config(database_url)

    command.upgrade(config, "head")

    connection = sqlite3.connect(database_path)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
            )
        }
        assert tables == set(Base.metadata.tables) | {"alembic_version"}

        revision = connection.execute("select version_num from alembic_version").fetchone()
        assert revision == ("0004_progress",)

        for table_name, table in Base.metadata.tables.items():
            columns = {
                row[1]
                for row in connection.execute(f"pragma table_info('{table_name}')")  # noqa: S608
            }
            assert columns == set(table.columns.keys()), table_name

        index_sql = connection.execute(
            "select sql from sqlite_master "
            "where type = 'index' and name = 'uq_plantings_active_plot'"
        ).fetchone()
        assert index_sql is not None
        assert "UNIQUE" in index_sql[0].upper()
        assert "status <> 'exhausted'" in index_sql[0]
    finally:
        connection.close()

    command.downgrade(config, "base")

    connection = sqlite3.connect(database_path)
    try:
        remaining = {
            row[0]
            for row in connection.execute(
                "select name from sqlite_master where type = 'table' and name not like 'sqlite_%'"
            )
        }
        assert remaining == {"alembic_version"}
    finally:
        connection.close()
