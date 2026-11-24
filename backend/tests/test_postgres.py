"""Validação em PostgreSQL real: migrações e requisições realmente concorrentes.

Estes testes só rodam com ``AGRO_TEST_DATABASE_URL`` apontando para um PostgreSQL
(banco terminado em ``_test``). Em SQLite eles são pulados, pois SQLite não
reproduz as travas de linha (``FOR UPDATE``) nem conexões concorrentes.

    AGRO_TEST_DATABASE_URL=postgresql+asyncpg://agro:agro@localhost:5432/agroetech_test \
        pytest tests/test_postgres.py -v
"""

import asyncio
import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from httpx import AsyncClient, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.models  # noqa: F401
from app.core.time import ensure_utc, utcnow
from app.models.animal import Animal
from app.models.base import Base
from app.models.planting import Planting
from app.models.progress import PlayerProgress
from app.models.talent import TalentPreset
from app.models.wallet import Wallet, WalletLedgerEntry
from tests.conftest import IS_POSTGRES, TEST_DATABASE_URL, _ensure_postgres_database
from tests.helpers import boost_player, inventory_quantities, set_planting_schedule
from tests.migration_utils import actual_schema, diff_schemas, expected_schema

pytestmark = pytest.mark.skipif(
    not IS_POSTGRES, reason="requer AGRO_TEST_DATABASE_URL apontando para um PostgreSQL de teste"
)

Headers = dict[str, str]
BACKEND_DIR = Path(__file__).resolve().parents[1]


# ------------------------------------------------------------------ migrações
def test_migrations_build_the_same_schema_as_the_models_and_can_roll_back() -> None:
    async def reset() -> None:
        await _ensure_postgres_database(TEST_DATABASE_URL)
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.exec_driver_sql("drop table if exists alembic_version")
        await engine.dispose()

    async def snapshot() -> dict:
        engine = create_async_engine(TEST_DATABASE_URL)
        async with engine.connect() as connection:
            shapes = await connection.run_sync(actual_schema)
        await engine.dispose()
        return shapes

    asyncio.run(reset())
    config = Config()
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)

    command.upgrade(config, "head")
    assert diff_schemas(expected_schema(), asyncio.run(snapshot())) == []

    # Subir de novo é no-op e descer até a base remove tudo.
    command.upgrade(config, "head")
    command.downgrade(config, "base")
    assert asyncio.run(snapshot()) == {}


# ---------------------------------------------------------------- concorrência
def _buy(
    client: AsyncClient, headers: Headers, property_id: str, item: str, key: str | None = None
):
    extra = {"Idempotency-Key": key} if key else {}
    return client.post(
        f"/api/v1/properties/{property_id}/market/buy",
        headers={**headers, **extra},
        json={"item_id": item, "quantity": 1},
    )


def _statuses(responses: list[Response]) -> list[int]:
    return sorted(r.status_code for r in responses)


async def test_concurrent_purchases_never_overdraw_the_wallet(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=1)  # saldo 100
    responses = await asyncio.gather(
        *[_buy(client, auth_headers, property_id, "seed_cafe") for _ in range(12)]  # 90 AGC cada
    )
    assert _statuses(responses).count(200) == 1
    assert (await client.get("/api/v1/wallet", headers=auth_headers)).json()["balance"] == 10
    assert (await inventory_quantities(client, property_id, auth_headers))["seed_cafe"] == 2

    async with session_factory() as session:
        total = await session.scalar(select(func.sum(WalletLedgerEntry.amount)))
        stored = await session.scalar(select(Wallet.balance))
    assert total == stored == 10


async def test_same_idempotency_key_sent_concurrently_charges_once(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
) -> None:
    responses = await asyncio.gather(
        *[
            _buy(client, auth_headers, property_id, "seed_milho", key="chave-concorrente-1")
            for _ in range(8)
        ]
    )
    assert set(_statuses(responses)) == {200}
    assert sum(1 for r in responses if r.json()["replayed"] is False) == 1
    assert (await client.get("/api/v1/wallet", headers=auth_headers)).json()["balance"] == 92


async def test_concurrent_wallet_first_access_creates_one_wallet(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    responses = await asyncio.gather(
        *[client.get("/api/v1/wallet", headers=auth_headers) for _ in range(10)]
    )
    assert set(_statuses(responses)) == {200}
    assert {r.json()["balance"] for r in responses} == {100}
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(Wallet)) == 1
        grants = await session.scalar(
            select(func.count())
            .select_from(WalletLedgerEntry)
            .where(WalletLedgerEntry.kind == "initial_grant")
        )
        assert grants == 1


async def test_concurrent_first_access_creates_single_progress_and_preset(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    responses = await asyncio.gather(
        *[client.get("/api/v1/talents", headers=auth_headers) for _ in range(8)],
        *[client.get("/api/v1/progress", headers=auth_headers) for _ in range(8)],
    )
    assert set(_statuses(responses)) == {200}
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(TalentPreset)) == 1
        assert await session.scalar(select(func.count()).select_from(PlayerProgress)) == 1


async def test_concurrent_registration_with_same_email_creates_one_account(
    client: AsyncClient,
) -> None:
    payload = {"email": "corrida@agro.com.br", "username": "corrida", "password": "colheita2026"}
    responses = await asyncio.gather(
        *[client.post("/api/v1/auth/register", json=payload) for _ in range(8)]
    )
    codes = _statuses(responses)
    assert codes.count(201) == 1 and set(codes) <= {201, 409}


async def test_concurrent_property_creation_yields_one_farm(
    client: AsyncClient,
    auth_headers: Headers,
) -> None:
    body = {"name": "Fazenda Corrida", "area_hectares": 5, "plot_count": 6}
    responses = await asyncio.gather(
        *[client.post("/api/v1/properties", headers=auth_headers, json=body) for _ in range(6)]
    )
    codes = _statuses(responses)
    assert codes.count(201) == 1 and set(codes) <= {201, 409}
    listing = await client.get("/api/v1/properties", headers=auth_headers)
    assert len(listing.json()) == 1


async def test_concurrent_upgrades_charge_the_building_only_once(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=6, agc=50)  # saldo 150
    url = f"/api/v1/properties/{property_id}/buildings/poco/upgrade"
    responses = await asyncio.gather(*[client.post(url, headers=auth_headers) for _ in range(8)])
    # Nível 1 custa 60 e o nível 2 custa 200 (> saldo restante): só a primeira passa.
    assert _statuses(responses).count(200) == 1
    assert (await client.get("/api/v1/wallet", headers=auth_headers)).json()["balance"] == 90
    state = (
        await client.get(f"/api/v1/properties/{property_id}/buildings", headers=auth_headers)
    ).json()
    assert next(b for b in state["buildings"] if b["id"] == "poco")["level"] == 1


async def test_concurrent_crafting_never_exceeds_the_station_slots(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=12, agc=1000)
    assert (
        await client.post(
            f"/api/v1/properties/{property_id}/buildings/moinho/upgrade", headers=auth_headers
        )
    ).status_code == 200
    async with session_factory() as session:
        from app.models.inventory import InventoryItem

        session.add(
            InventoryItem(property_id=uuid.UUID(property_id), item_id="crop_milho", quantity=60)
        )
        await session.commit()

    responses = await asyncio.gather(
        *[
            client.post(
                f"/api/v1/properties/{property_id}/crafting/start",
                headers=auth_headers,
                json={"recipe_id": "farinha", "batches": 1},
            )
            for _ in range(10)
        ]
    )
    assert _statuses(responses).count(200) == 1  # Moinho nível 1 = 1 vaga
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 57


async def test_concurrent_harvest_and_collect_pay_out_once(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Colheita: o mesmo plantio colhido por várias requisições rende uma vez só.
    planted = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "milho", "plot_index": 0},
    )
    now = utcnow()
    await set_planting_schedule(
        session_factory,
        planted.json()["id"],
        next_ready_at=now - timedelta(minutes=10),
        last_sync_at=now - timedelta(minutes=15),
    )
    before = (await inventory_quantities(client, property_id, auth_headers))["crop_milho"]
    harvests = await asyncio.gather(
        *[
            client.post(f"/api/v1/plantings/{planted.json()['id']}/harvest", headers=auth_headers)
            for _ in range(6)
        ]
    )
    assert _statuses(harvests).count(200) == 1
    after = (await inventory_quantities(client, property_id, auth_headers))["crop_milho"]
    assert after - before == 3
    async with session_factory() as session:
        planting = await session.get(Planting, uuid.UUID(planted.json()["id"]))
        assert planting is not None and planting.stored_cycles == 0

    # Animais: o estoque do animal é coletado uma única vez.
    await boost_player(client, auth_headers, session_factory, level=10, agc=1000)
    await client.post(
        f"/api/v1/properties/{property_id}/buildings/galinheiro/upgrade", headers=auth_headers
    )
    await client.post(
        f"/api/v1/properties/{property_id}/animals/buy",
        headers=auth_headers,
        json={"species": "galinha"},
    )
    async with session_factory() as session:
        animal = (await session.scalars(select(Animal))).one()
        animal.stored = 8
        animal.fed_until = ensure_utc(utcnow()) - timedelta(hours=1)
        await session.commit()
    collects = await asyncio.gather(
        *[
            client.post(f"/api/v1/properties/{property_id}/animals/collect", headers=auth_headers)
            for _ in range(6)
        ]
    )
    assert _statuses(collects).count(200) == 1
    assert (await inventory_quantities(client, property_id, auth_headers))["animal_ovo"] == 8
