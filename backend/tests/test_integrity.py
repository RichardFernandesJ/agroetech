"""Integridade: corridas viram 409, regras únicas valem no banco e o diff de esquema funciona."""

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.errors import register_exception_handlers
from app.models.property import Property
from tests.migration_utils import TableShape, diff_schemas


async def test_unique_violation_becomes_a_409_instead_of_a_500() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom() -> None:
        raise IntegrityError("insert", {}, Exception("duplicate key"))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/boom")

    assert response.status_code == 409
    assert response.json()["code"] == "conflict"
    assert "Tente novamente" in response.json()["detail"]


async def test_database_allows_only_one_property_per_owner(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    me = await client.get("/api/v1/auth/me", headers=auth_headers)
    owner_id = uuid.UUID(me.json()["id"])

    async with session_factory() as session:
        session.add(Property(owner_id=owner_id, name="Fazenda Clone", area_hectares=1.0))
        with pytest.raises(IntegrityError):
            await session.commit()


def test_schema_diff_reports_drift_in_both_directions() -> None:
    expected = {
        "a": TableShape(columns={"id", "x"}, indexes={"ix_a_x"}, uniques={"uq_a"}, checks={"ck_a"}),
        "b": TableShape(columns={"id"}),
    }
    actual = {
        "a": TableShape(columns={"id"}, indexes={"ix_a_extra"}, uniques={"uq_a"}, checks=set()),
        "c": TableShape(columns={"id"}),
    }
    problems = diff_schemas(expected, actual)
    assert "tabela ausente no banco: b" in problems
    assert "tabela fora dos models: c" in problems
    assert "a: falta coluna «x» nas migrações" in problems
    assert "a: falta índice «ix_a_x» nas migrações" in problems
    assert "a: índice «ix_a_extra» só existe nas migrações" in problems
    assert "a: falta restrição de checagem «ck_a» nas migrações" in problems
    assert diff_schemas(expected, expected) == []


async def test_wallet_update_is_compare_and_set_even_without_row_locks(
    client: AsyncClient,
    auth_headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Duas operações que leram o mesmo saldo: só a primeira a gravar vale (sem duplo gasto)."""
    from app.core.exceptions import ConflictError
    from app.repositories.wallet_repository import WalletRepository
    from app.services.wallet_service import WalletService

    await client.get("/api/v1/wallet", headers=auth_headers)  # cria a carteira (100 AGC)
    user_id = uuid.UUID((await client.get("/api/v1/auth/me", headers=auth_headers)).json()["id"])

    async with session_factory() as first, session_factory() as second:
        service_a = WalletService(first, WalletRepository(first))
        service_b = WalletService(second, WalletRepository(second))
        wallet_a = await WalletRepository(first).get_by_user_id(user_id)
        wallet_b = await WalletRepository(second).get_by_user_id(user_id)  # leu o mesmo 100
        assert wallet_a is not None and wallet_b is not None

        await service_a.apply(wallet_a, kind="seed_purchase", amount=-90)
        await first.commit()

        with pytest.raises(ConflictError):
            await service_b.apply(wallet_b, kind="seed_purchase", amount=-90)
        await second.rollback()

    assert (await client.get("/api/v1/wallet", headers=auth_headers)).json()["balance"] == 10


async def test_inventory_debit_is_atomic_even_without_row_locks(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Dois débitos que leram o mesmo estoque: o segundo não pode passar (sem item duplicado)."""
    from app.models.inventory import InventoryItem
    from app.repositories.inventory_repository import InventoryRepository

    async with session_factory() as session:
        session.add(
            InventoryItem(property_id=uuid.UUID(property_id), item_id="crop_milho", quantity=10)
        )
        await session.commit()

    async with session_factory() as first, session_factory() as second:
        repo_a, repo_b = InventoryRepository(first), InventoryRepository(second)
        item_a = await repo_a.get_item(uuid.UUID(property_id), "crop_milho")
        item_b = await repo_b.get_item(uuid.UUID(property_id), "crop_milho")  # também leu 10
        assert item_a is not None and item_b is not None

        assert await repo_a.try_decrement(item_a, 10) is True
        await first.commit()
        assert await repo_b.try_decrement(item_b, 10) is False
        await second.rollback()

    async with session_factory() as session:
        row = await InventoryRepository(session).get_item(uuid.UUID(property_id), "crop_milho")
        assert row is not None and row.quantity == 0
