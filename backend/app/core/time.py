"""Utilitários de tempo.

O PostgreSQL devolve datetimes com timezone, enquanto o SQLite (usado nos
testes) devolve datetimes "naive". Centralizar a normalização evita
comparações inválidas entre datetimes aware e naive.
"""

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
