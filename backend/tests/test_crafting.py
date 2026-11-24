"""Fase 5: fabricação (estações, receitas, trabalhos com duração e coleta)."""

import uuid
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.time import ensure_utc, utcnow
from app.models.inventory import InventoryItem
from app.models.production_job import ProductionJob
from tests.helpers import boost_player, inventory_quantities

Headers = dict[str, str]


def _url(property_id: str, tail: str = "") -> str:
    return f"/api/v1/properties/{property_id}/crafting{tail}"


async def _state(client: AsyncClient, headers: Headers, property_id: str) -> dict:
    response = await client.get(_url(property_id), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _build(client: AsyncClient, headers: Headers, property_id: str, building: str) -> None:
    response = await client.post(
        f"/api/v1/properties/{property_id}/buildings/{building}/upgrade", headers=headers
    )
    assert response.status_code == 200, response.text


async def _start(
    client: AsyncClient,
    headers: Headers,
    property_id: str,
    recipe: str,
    batches: int = 1,
    key: str | None = None,
):
    extra = {"Idempotency-Key": key} if key else {}
    return await client.post(
        _url(property_id, "/start"),
        headers={**headers, **extra},
        json={"recipe_id": recipe, "batches": batches},
    )


async def _give(
    session_factory: async_sessionmaker[AsyncSession], property_id: str, item: str, quantity: int
) -> None:
    async with session_factory() as session:
        row = await session.scalar(
            select(InventoryItem).where(
                InventoryItem.property_id == uuid.UUID(property_id), InventoryItem.item_id == item
            )
        )
        if row is None:
            session.add(
                InventoryItem(property_id=uuid.UUID(property_id), item_id=item, quantity=quantity)
            )
        else:
            row.quantity += quantity
        await session.commit()


async def _finish_all(session_factory: async_sessionmaker[AsyncSession]) -> None:
    """Faz todos os trabalhos em aberto terminarem agora (simula o tempo passando)."""
    async with session_factory() as session:
        for job in (await session.scalars(select(ProductionJob))).all():
            job.finish_at = utcnow() - timedelta(seconds=1)
        await session.commit()


async def _setup(
    client: AsyncClient,
    headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    *buildings: str,
    level: int = 12,
    agc: int = 5000,
) -> None:
    await boost_player(client, headers, session_factory, level=level, agc=agc)
    for building in buildings:
        await _build(client, headers, property_id, building)


async def test_requires_authentication(client: AsyncClient, property_id: str) -> None:
    assert (await client.get(_url(property_id))).status_code == 401
    assert (await client.post(_url(property_id, "/collect"))).status_code == 401


async def test_initial_state_lists_recipes_and_what_is_missing(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    state = await _state(client, auth_headers, property_id)
    assert {s["building_id"] for s in state["stations"]} == {"moinho", "padaria", "queijaria"}
    assert all(s["job_slots"] == 0 for s in state["stations"])
    assert {r["id"] for r in state["recipes"]} == {"farinha", "pao", "bolo", "queijo", "manteiga"}
    farinha = next(r for r in state["recipes"] if r["id"] == "farinha")
    assert farinha["can_craft"] is False and "Moinho" in farinha["blocked_reason"]
    assert farinha["inputs"] == [
        {"item_id": "crop_milho", "name": "Milho", "per_batch": 3, "have": 0}
    ]


async def test_start_requires_station_level_and_inputs(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert (await _start(client, auth_headers, property_id, "farinha")).status_code == 422

    await _setup(client, auth_headers, property_id, session_factory, level=3, agc=1000)
    no_station = await _start(client, auth_headers, property_id, "farinha")
    assert no_station.status_code == 422 and "Moinho" in no_station.json()["detail"]

    await _build(client, auth_headers, property_id, "moinho")
    no_inputs = await _start(client, auth_headers, property_id, "farinha")
    assert no_inputs.status_code == 422 and "insuficiente" in no_inputs.json()["detail"]

    low_level = await _start(client, auth_headers, property_id, "pao")  # padaria + nível 5
    assert low_level.status_code == 422


async def test_unknown_recipe_and_invalid_batches(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(client, auth_headers, property_id, session_factory, "moinho")
    assert (await _start(client, auth_headers, property_id, "elixir")).status_code == 404
    for batches in (0, 25, -1):
        response = await _start(client, auth_headers, property_id, "farinha", batches)
        assert response.status_code == 422


async def test_full_cycle_start_wait_and_collect(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(client, auth_headers, property_id, session_factory, "moinho")
    await _give(session_factory, property_id, "crop_milho", 9)

    started = await _start(client, auth_headers, property_id, "farinha", 3)
    assert started.status_code == 200, started.text
    moinho = next(s for s in started.json()["stations"] if s["building_id"] == "moinho")
    assert (moinho["used_slots"], moinho["job_slots"]) == (1, 1)
    job = moinho["jobs"][0]
    assert (job["batches"], job["output_quantity"], job["ready"]) == (3, 3, False)
    assert 1700 < job["seconds_left"] <= 1800  # 600 s x 3 lotes
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 0

    # Ainda não terminou: nada para coletar e a estação segue ocupada.
    early = await client.post(_url(property_id, "/collect"), headers=auth_headers)
    assert early.status_code == 422
    await _give(session_factory, property_id, "crop_milho", 3)
    busy = await _start(client, auth_headers, property_id, "farinha")
    assert busy.status_code == 422 and "vagas" in busy.json()["detail"]

    await _finish_all(session_factory)
    collected = await client.post(_url(property_id, "/collect"), headers=auth_headers)
    assert collected.status_code == 200, collected.text
    body = collected.json()
    assert body["collected"] == {"processed_farinha": 3} and body["xp_gained"] == 12
    assert (await inventory_quantities(client, property_id, auth_headers))["processed_farinha"] == 3
    assert next(s for s in body["stations"] if s["building_id"] == "moinho")["used_slots"] == 0

    # A vaga foi liberada e coletar duas vezes não duplica nada.
    again = await client.post(_url(property_id, "/collect"), headers=auth_headers)
    assert again.status_code == 422
    assert (await _start(client, auth_headers, property_id, "farinha")).status_code == 200


async def test_failed_start_changes_nothing(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """Faltando um insumo, os que já seriam gastos não podem sumir (atomicidade)."""
    await _setup(client, auth_headers, property_id, session_factory, "padaria", level=12)
    await _give(session_factory, property_id, "processed_farinha", 2)
    await _give(session_factory, property_id, "animal_ovo", 1)  # bolo pede 2 ovos e 1 leite

    response = await _start(client, auth_headers, property_id, "bolo")
    assert response.status_code == 422
    stock = await inventory_quantities(client, property_id, auth_headers)
    assert (stock["processed_farinha"], stock["animal_ovo"]) == (2, 1)
    assert (await _state(client, auth_headers, property_id))["stations"][1]["used_slots"] == 0


async def test_chain_milho_to_pao_and_sell(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(client, auth_headers, property_id, session_factory, "moinho", "padaria")
    await _give(session_factory, property_id, "crop_milho", 6)
    await _give(session_factory, property_id, "animal_ovo", 2)

    assert (await _start(client, auth_headers, property_id, "farinha", 2)).status_code == 200
    await _finish_all(session_factory)
    assert (
        await client.post(_url(property_id, "/collect"), headers=auth_headers)
    ).status_code == 200

    # 2 farinhas + 1 ovo = 3 pães por lote.
    assert (await _start(client, auth_headers, property_id, "pao", 1)).status_code == 200
    await _finish_all(session_factory)
    collected = await client.post(_url(property_id, "/collect"), headers=auth_headers)
    assert collected.json()["collected"] == {"processed_pao": 3}

    sold = await client.post(
        f"/api/v1/properties/{property_id}/market/sell",
        headers=auth_headers,
        json={"item_id": "processed_pao", "quantity": 3},
    )
    assert sold.status_code == 200, sold.text
    assert (sold.json()["gross"], sold.json()["fee"]) == (120, 6)


async def test_station_upgrades_add_slots_and_speed(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(client, auth_headers, property_id, session_factory, "moinho", "moinho", level=12)
    state = await _state(client, auth_headers, property_id)
    moinho = next(s for s in state["stations"] if s["building_id"] == "moinho")
    assert (moinho["level"], moinho["job_slots"], moinho["time_bonus_bp"]) == (2, 2, -500)

    await _give(session_factory, property_id, "crop_milho", 6)
    for _ in range(2):  # 2 vagas
        assert (await _start(client, auth_headers, property_id, "farinha")).status_code == 200
    third = await _start(client, auth_headers, property_id, "farinha")
    assert third.status_code == 422

    async with session_factory() as session:
        job = (await session.scalars(select(ProductionJob))).first()
        assert job is not None
        seconds = (ensure_utc(job.finish_at) - ensure_utc(job.started_at)).total_seconds()
        assert round(seconds) == 570  # 600 s com -5% do Moinho nível 2


async def test_start_is_idempotent(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(client, auth_headers, property_id, session_factory, "moinho", "moinho")
    await _give(session_factory, property_id, "crop_milho", 9)

    first = await _start(client, auth_headers, property_id, "farinha", 1, key="producao-0001")
    second = await _start(client, auth_headers, property_id, "farinha", 1, key="producao-0001")
    assert first.json()["replayed"] is False and second.json()["replayed"] is True
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 6
    async with session_factory() as session:
        assert len((await session.scalars(select(ProductionJob))).all()) == 1

    other = await _start(client, auth_headers, property_id, "farinha", 2, key="producao-0001")
    assert other.status_code == 422


async def test_other_players_cannot_use_my_property(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(client, auth_headers, property_id, session_factory, "moinho")
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bia@agro.com.br", "username": "bia_roca", "password": "colheita2026"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"login": "bia@agro.com.br", "password": "colheita2026"}
    )
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get(_url(property_id), headers=other)).status_code == 404
    assert (await _start(client, other, property_id, "farinha")).status_code == 404
    assert (await client.post(_url(property_id, "/collect"), headers=other)).status_code == 404


async def test_cheese_and_butter_share_the_dairy_slots(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _setup(client, auth_headers, property_id, session_factory, "queijaria", level=12)
    await _give(session_factory, property_id, "animal_leite", 10)
    assert (await _start(client, auth_headers, property_id, "queijo")).status_code == 200
    # 1 vaga só: manteiga precisa esperar.
    assert (await _start(client, auth_headers, property_id, "manteiga")).status_code == 422
    await _finish_all(session_factory)
    await client.post(_url(property_id, "/collect"), headers=auth_headers)
    assert (await _start(client, auth_headers, property_id, "manteiga")).status_code == 200
