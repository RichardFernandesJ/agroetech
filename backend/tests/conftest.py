"""Fixtures compartilhadas dos testes.

Por padrão os testes usam SQLite em memória (com StaticPool para compartilhar a
mesma conexão) e substituem a dependência ``get_db``. Assim a suíte roda sem
Docker, enquanto produção usa PostgreSQL.

Para rodar a **mesma suíte em PostgreSQL real** (valida travas ``FOR UPDATE``,
índices parciais, JSON e concorrência de verdade), defina:

    AGRO_TEST_DATABASE_URL=postgresql+asyncpg://agro:agro@localhost:5432/agroetech_test

O nome do banco precisa terminar em ``_test``: o esquema é apagado e recriado a
cada teste, e esta trava impede que isso aconteça num banco de desenvolvimento.
O banco de teste é criado automaticamente se ainda não existir.
"""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (registra os models no metadata)
from app.core.database import get_db
from app.main import app
from app.models.base import Base

TEST_DATABASE_URL = os.environ.get("AGRO_TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
IS_POSTGRES = TEST_DATABASE_URL.startswith("postgresql")


async def _ensure_postgres_database(url: str) -> None:
    """Cria o banco de teste se ele não existir (e recusa bancos que não sejam de teste)."""
    parsed = make_url(url)
    name = parsed.database or ""
    if not name.endswith("_test"):
        pytest.exit(
            f"AGRO_TEST_DATABASE_URL aponta para «{name}»: o nome precisa terminar em _test "
            "porque a suíte apaga e recria as tabelas.",
            returncode=2,
        )
    admin = create_async_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        async with admin.connect() as connection:
            exists = await connection.scalar(
                text("select 1 from pg_database where datname = :name"), {"name": name}
            )
            if not exists:
                await connection.execute(text(f'create database "{name}"'))
    finally:
        await admin.dispose()


@pytest_asyncio.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    if IS_POSTGRES:
        await _ensure_postgres_database(TEST_DATABASE_URL)
        # Conexões independentes: permite testar requisições realmente concorrentes.
        test_engine = create_async_engine(TEST_DATABASE_URL, pool_size=20, max_overflow=0)
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    else:
        test_engine = create_async_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        async with test_engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
    )


@pytest_asyncio.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncClient]:
    async def override_get_db() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client
    app.dependency_overrides.clear()


@pytest.fixture
def user_payload() -> dict[str, str]:
    return {
        "email": "ana@agro.com.br",
        "username": "ana_fazendeira",
        "password": "colheita2026",
    }


@pytest_asyncio.fixture
async def auth_headers(
    client: AsyncClient,
    user_payload: dict[str, str],
) -> dict[str, str]:
    register = await client.post("/api/v1/auth/register", json=user_payload)
    assert register.status_code == 201, register.text

    login = await client.post(
        "/api/v1/auth/login",
        json={"login": user_payload["email"], "password": user_payload["password"]},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def property_id(client: AsyncClient, auth_headers: dict[str, str]) -> str:
    response = await client.post(
        "/api/v1/properties",
        headers=auth_headers,
        json={
            "name": "Fazenda Boa Vista",
            "area_hectares": 12.5,
            "plot_count": 6,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]
