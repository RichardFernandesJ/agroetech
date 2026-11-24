"""Fase 5: construções melhoráveis (Casa da Fazenda e Poço)."""

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.game.buildings import BUILDINGS, STARTING_PLOTS
from app.models.planting import Planting
from app.models.wallet import Wallet, WalletLedgerEntry
from tests.helpers import boost_player

Headers = dict[str, str]


async def _state(client: AsyncClient, headers: Headers, property_id: str) -> dict:
    response = await client.get(f"/api/v1/properties/{property_id}/buildings", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _building(state: dict, building_id: str) -> dict:
    return next(b for b in state["buildings"] if b["id"] == building_id)


async def _upgrade(
    client: AsyncClient,
    headers: Headers,
    property_id: str,
    building_id: str,
    key: str | None = None,
):
    extra = {"Idempotency-Key": key} if key else {}
    return await client.post(
        f"/api/v1/properties/{property_id}/buildings/{building_id}/upgrade",
        headers={**headers, **extra},
    )


async def _balance(client: AsyncClient, headers: Headers) -> int:
    return (await client.get("/api/v1/wallet", headers=headers)).json()["balance"]


def test_catalog_is_consistent() -> None:
    for definition in BUILDINGS.values():
        levels = [entry.level for entry in definition.levels]
        assert levels == sorted(set(levels)) and levels[-1] == definition.max_level
        costs = [
            entry.cost for entry in definition.levels if entry.level > definition.initial_level
        ]
        assert costs == sorted(costs), "custo cresce a cada nível"
        mins = [entry.min_player_level for entry in definition.levels]
        assert mins == sorted(mins), "exigência de nível cresce a cada nível"
    assert STARTING_PLOTS == 6
    assert BUILDINGS["sede"].levels[-1].plots == 12


async def test_catalog_is_public(client: AsyncClient) -> None:
    response = await client.get("/api/v1/catalog/buildings")
    assert response.status_code == 200
    body = {b["id"]: b for b in response.json()}
    assert set(body) == {"sede", "poco", "galinheiro", "estabulo"}
    assert [lvl["plots"] for lvl in body["sede"]["levels"]] == [6, 8, 10, 12]
    assert body["poco"]["levels"][0]["effects"] == [
        {"stat": "crop_grow_time", "value_bp": -200, "scope": None}
    ]


async def test_requires_authentication(client: AsyncClient, property_id: str) -> None:
    assert (await client.get(f"/api/v1/properties/{property_id}/buildings")).status_code == 401
    unauth = await client.post(f"/api/v1/properties/{property_id}/buildings/poco/upgrade")
    assert unauth.status_code == 401


async def test_initial_state(client: AsyncClient, auth_headers: Headers, property_id: str) -> None:
    state = await _state(client, auth_headers, property_id)
    assert state["plot_count"] == 6
    sede = _building(state, "sede")
    assert (sede["level"], sede["max_level"]) == (1, 4)
    assert sede["next"]["plots"] == 8
    poco = _building(state, "poco")
    assert poco["level"] == 0 and poco["current"] is None
    assert poco["can_upgrade"] is False
    assert "nível de jogador 2" in poco["blocked_reason"]


async def test_upgrade_requires_player_level_without_charging(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    response = await _upgrade(client, auth_headers, property_id, "poco")
    assert response.status_code == 422
    assert await _balance(client, auth_headers) == 100


async def test_upgrade_requires_funds_without_side_effects(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=10)
    response = await _upgrade(client, auth_headers, property_id, "sede")  # 150 > 100
    assert response.status_code == 422
    state = await _state(client, auth_headers, property_id)
    assert state["plot_count"] == 6 and _building(state, "sede")["level"] == 1
    assert _building(state, "sede")["blocked_reason"].startswith("Saldo insuficiente")
    assert await _balance(client, auth_headers) == 100


async def test_unknown_building_and_foreign_property(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=10, agc=1000)
    assert (await _upgrade(client, auth_headers, property_id, "castelo")).status_code == 404

    await client.post(
        "/api/v1/auth/register",
        json={"email": "bia@agro.com.br", "username": "bia_roca", "password": "colheita2026"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"login": "bia@agro.com.br", "password": "colheita2026"}
    )
    intruder = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await _upgrade(client, intruder, property_id, "poco")).status_code == 404
    listing = await client.get(f"/api/v1/properties/{property_id}/buildings", headers=intruder)
    assert listing.status_code == 404


async def test_well_upgrade_charges_and_speeds_up_new_plantings(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=2)
    response = await _upgrade(client, auth_headers, property_id, "poco")
    assert response.status_code == 200, response.text
    assert _building(response.json(), "poco")["level"] == 1
    assert await _balance(client, auth_headers) == 100 - 60

    planted = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "milho", "plot_index": 0},
    )
    assert planted.status_code == 201
    async with session_factory() as session:
        planting = await session.get(Planting, uuid.UUID(planted.json()["id"]))
        assert planting is not None
        assert planting.grow_seconds == 294  # 300 s com -2% do poço nível 1
        assert planting.modifiers is not None and planting.modifiers["crop_grow_time"] == -200


async def test_well_stacks_with_talents_through_the_modifier_engine(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=5, agc=500)
    await _upgrade(client, auth_headers, property_id, "poco")  # -2%
    talent = await client.post(
        "/api/v1/talents/allocate",
        headers=auth_headers,
        json={"node_id": "agro_sementes_vigorosas"},
    )
    assert talent.status_code == 200  # -2%

    planted = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "milho", "plot_index": 0},
    )
    async with session_factory() as session:
        planting = await session.get(Planting, uuid.UUID(planted.json()["id"]))
        assert planting is not None and planting.grow_seconds == 288  # 300 s com -4%


async def test_house_upgrade_unlocks_new_plots(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=3, agc=100)

    def plant(plot: int):
        return client.post(
            f"/api/v1/properties/{property_id}/plantings",
            headers=auth_headers,
            json={"crop_id": "milho", "plot_index": plot},
        )

    assert (await plant(6)).status_code == 422  # talhão 7 ainda não existe

    response = await _upgrade(client, auth_headers, property_id, "sede")
    assert response.status_code == 200, response.text
    assert response.json()["plot_count"] == 8
    detail = await client.get(f"/api/v1/properties/{property_id}", headers=auth_headers)
    assert detail.json()["plot_count"] == 8
    assert (await plant(6)).status_code == 201
    assert (await plant(8)).status_code == 422


async def test_max_level_and_full_progression(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=50, agc=10_000)
    for _ in range(3):
        assert (await _upgrade(client, auth_headers, property_id, "poco")).status_code == 200
    again = await _upgrade(client, auth_headers, property_id, "poco")
    assert again.status_code == 422 and "máximo" in again.json()["detail"]

    for _ in range(3):
        assert (await _upgrade(client, auth_headers, property_id, "sede")).status_code == 200
    state = await _state(client, auth_headers, property_id)
    assert state["plot_count"] == 12
    assert all(_building(state, building_id)["next"] is None for building_id in ("sede", "poco"))
    assert await _balance(client, auth_headers) == 100 + 10_000 - (60 + 200 + 500) - (
        150 + 400 + 900
    )


async def test_idempotency_prevents_double_charge(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=10, agc=500)
    first = await _upgrade(client, auth_headers, property_id, "poco", "melhoria-0001")
    second = await _upgrade(client, auth_headers, property_id, "poco", "melhoria-0001")
    assert first.status_code == second.status_code == 200
    assert first.json()["replayed"] is False and second.json()["replayed"] is True
    assert _building(second.json(), "poco")["level"] == 1
    assert await _balance(client, auth_headers) == 100 + 500 - 60

    other = await _upgrade(client, auth_headers, property_id, "sede", "melhoria-0001")
    assert other.status_code == 409


async def test_ledger_reconciles_after_upgrades(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=10, agc=700)
    await _upgrade(client, auth_headers, property_id, "poco")
    await _upgrade(client, auth_headers, property_id, "sede")
    async with session_factory() as session:
        total = await session.scalar(select(func.sum(WalletLedgerEntry.amount)))
        stored = await session.scalar(select(Wallet.balance))
    assert total == stored == await _balance(client, auth_headers)
    ledger = (await client.get("/api/v1/wallet/ledger", headers=auth_headers)).json()
    assert {"building_upgrade"} <= {entry["kind"] for entry in ledger["entries"]}


async def test_player_can_have_only_one_farm_with_fixed_starting_plots(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    second = await client.post(
        "/api/v1/properties",
        headers=auth_headers,
        json={"name": "Outra Fazenda", "area_hectares": 5, "plot_count": 6},
    )
    assert second.status_code == 409


async def test_new_farm_cannot_start_with_extra_plots(
    client: AsyncClient, auth_headers: Headers
) -> None:
    response = await client.post(
        "/api/v1/properties",
        headers=auth_headers,
        json={"name": "Fazenda Grande", "area_hectares": 5, "plot_count": 12},
    )
    assert response.status_code == 422
