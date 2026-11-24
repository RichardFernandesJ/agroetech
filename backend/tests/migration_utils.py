"""Comparação entre o esquema criado pelas migrações e os models (SQLite e PostgreSQL)."""

from dataclasses import dataclass, field

from sqlalchemy import CheckConstraint, Index, UniqueConstraint, inspect
from sqlalchemy.engine import Connection

from app.models.base import Base

LABELS = {
    "columns": "coluna",
    "indexes": "índice",
    "uniques": "restrição única",
    "checks": "restrição de checagem",
}


@dataclass(slots=True)
class TableShape:
    columns: set[str] = field(default_factory=set)
    indexes: set[str] = field(default_factory=set)
    uniques: set[str] = field(default_factory=set)
    checks: set[str] = field(default_factory=set)


def expected_schema() -> dict[str, TableShape]:
    """O que os models dizem que deve existir."""
    shapes: dict[str, TableShape] = {}
    for name, table in Base.metadata.tables.items():
        shape = TableShape(columns=set(table.columns.keys()))
        for constraint in table.constraints:
            if isinstance(constraint, UniqueConstraint) and constraint.name:
                shape.uniques.add(constraint.name)
            if isinstance(constraint, CheckConstraint) and constraint.name:
                shape.checks.add(str(constraint.name))
        for index in table.indexes:
            if isinstance(index, Index) and index.name:
                (shape.uniques if index.unique else shape.indexes).add(index.name)
        # Colunas com unique=True geram uma restrição/índice sem nome definido: ignoradas.
        shapes[name] = shape
    return shapes


def actual_schema(connection: Connection) -> dict[str, TableShape]:
    """O que o banco realmente tem depois das migrações."""
    inspector = inspect(connection)
    shapes: dict[str, TableShape] = {}
    for name in inspector.get_table_names():
        if name == "alembic_version":
            continue
        shape = TableShape(columns={col["name"] for col in inspector.get_columns(name)})
        for index in inspector.get_indexes(name):
            if index["name"]:
                (shape.uniques if index.get("unique") else shape.indexes).add(index["name"])
        for unique in inspector.get_unique_constraints(name):
            if unique["name"]:
                shape.uniques.add(unique["name"])
        for check in inspector.get_check_constraints(name):
            if check["name"]:
                shape.checks.add(check["name"])
        shapes[name] = shape
    return shapes


def diff_schemas(expected: dict[str, TableShape], actual: dict[str, TableShape]) -> list[str]:
    """Diferenças legíveis (vazio = migrações e models estão em paridade)."""
    problems: list[str] = []
    for missing in sorted(set(expected) - set(actual)):
        problems.append(f"tabela ausente no banco: {missing}")
    for extra in sorted(set(actual) - set(expected)):
        problems.append(f"tabela fora dos models: {extra}")
    for table in sorted(set(expected) & set(actual)):
        for attr, label in LABELS.items():
            want, have = getattr(expected[table], attr), getattr(actual[table], attr)
            for item in sorted(want - have):
                problems.append(f"{table}: falta {label} «{item}» nas migrações")
            for item in sorted(have - want):
                problems.append(f"{table}: {label} «{item}» só existe nas migrações")
    return problems
