"""Ramos Pecuária e Indústria: os talentos chegam de verdade aos animais e à fabricação."""

import uuid
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.time import ensure_utc, utcnow
from app.models.animal import Animal
from app.models.inventory import InventoryItem
from app.models.production_job import ProductionJob
from tests.helpers import boost_player

Headers = dict[str, str]


async def _allocate(client: AsyncClient, headers: Headers, *node_ids: str) -> None:
    for node_id in node_ids:
        response = await client.post(
            "/api/v1/talents/allocate", headers=headers, json={"node_id": node_id}
        )
        assert response.status_code == 200, (node_id, response.text)


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


async def _upgrade(client: AsyncClient, headers: Headers, property_id: str, building: str) -> None:
    response = await client.post(
        f"/api/v1/properties/{property_id}/buildings/{building}/upgrade", headers=headers
    )
    assert response.status_code == 200, response.text


async def _animals(client: AsyncClient, headers: Headers, property_id: str) -> dict:
    response = await client.get(f"/api/v1/properties/{property_id}/animals", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _feed(
    client: AsyncClient, headers: Headers, property_id: str, animal_id: str, units: int
):
    return await client.post(
        f"/api/v1/properties/{property_id}/animals/{animal_id}/feed",
        headers=headers,
        json={"units": units},
    )


async def _farm_with_chicken(
    client: AsyncClient,
    headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> str:
    await boost_player(client, headers, session_factory, level=50, agc=3000)
    await _upgrade(client, headers, property_id, "galinheiro")
    bought = await client.post(
        f"/api/v1/properties/{property_id}/animals/buy",
        headers=headers,
        json={"species": "galinha"},
    )
    assert bought.status_code == 200, bought.text
    await _give(session_factory, property_id, "crop_milho", 60)
    return bought.json()["animals"][0]["id"]


async def _make_hungry(session_factory: async_sessionmaker[AsyncSession]) -> None:
    async with session_factory() as session:
        for animal in (await session.scalars(select(Animal))).all():
            animal.fed_until = utcnow() - timedelta(hours=1)
            animal.last_sync_at = utcnow() - timedelta(minutes=1)
        await session.commit()


async def test_new_branches_are_open_in_the_catalog(client: AsyncClient) -> None:
    body = (await client.get("/api/v1/catalog/talents")).json()
    open_branches = {b["id"] for b in body["branches"] if b["available"]}
    assert {"pecuaria", "industria"} <= open_branches
    ids = {n["id"] for n in body["nodes"]}
    assert {"pec_mestre_rebanho", "ind_fabrica", "hib_laticinios", "hib_feira_pecuaria"} <= ids
    assert len(body["nodes"]) == 55


async def test_animal_talents_speed_and_yield_are_snapshotted_when_feeding(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    animal_id = await _farm_with_chicken(client, auth_headers, property_id, session_factory)
    await _allocate(client, auth_headers, "pec_pasto_verde", "pec_manejo")  # +2% e -2% de tempo

    fed = await _feed(client, auth_headers, property_id, animal_id, 4)
    assert fed.status_code == 200, fed.text
    chicken = fed.json()["animals"][0]
    assert chicken["produce_seconds"] == 882  # 900 s com -2%
    assert chicken["yield_bonus_bp"] == 200

    # Redefinir os talentos não altera a produção já em curso (ração acumulada).
    assert (await client.post("/api/v1/talents/reset", headers=auth_headers)).status_code == 200
    again = (await _animals(client, auth_headers, property_id))["animals"][0]
    assert (again["produce_seconds"], again["yield_bonus_bp"]) == (882, 200)

    # Depois da fome, a próxima alimentação passa a valer sem os talentos.
    await _make_hungry(session_factory)
    refed = await _feed(client, auth_headers, property_id, animal_id, 1)
    assert refed.status_code == 200
    plain = refed.json()["animals"][0]
    assert (plain["produce_seconds"], plain["yield_bonus_bp"]) == (900, 0)


async def test_feed_efficiency_makes_the_feed_last_longer(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    animal_id = await _farm_with_chicken(client, auth_headers, property_id, session_factory)
    await _allocate(client, auth_headers, "pec_cocho_farto")  # ração rende 4% mais

    fed = await _feed(client, auth_headers, property_id, animal_id, 1)
    seconds = fed.json()["animals"][0]["fed_seconds_left"]
    assert 2170 < seconds <= 2184  # 2100 s x 1,04


async def test_animal_yield_applies_when_collecting(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    animal_id = await _farm_with_chicken(client, auth_headers, property_id, session_factory)
    await _allocate(client, auth_headers, "pec_pasto_verde")  # +2%
    await _feed(client, auth_headers, property_id, animal_id, 13)

    async with session_factory() as session:
        animal = (await session.scalars(select(Animal))).one()
        animal.stored = 32
        await session.commit()

    collected = await client.post(
        f"/api/v1/properties/{property_id}/animals/collect", headers=auth_headers
    )
    assert collected.status_code == 200, collected.text
    # 32 ovos com +2% = 32,64: sai 32 ou 33 (sorteio determinístico), nunca menos.
    assert collected.json()["products"]["animal_ovo"] in (32, 33)


async def test_industry_talents_shorten_jobs_and_raise_output(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=50, agc=3000)
    await _upgrade(client, auth_headers, property_id, "moinho")
    await _give(session_factory, property_id, "crop_milho", 72)
    # Tempo: -2% (global) e -5% (Moinho). Rendimento: +2% e +5%.
    await _allocate(client, auth_headers, "ind_ferramentas", "ind_boa_receita", "ind_moleiro")

    started = await client.post(
        f"/api/v1/properties/{property_id}/crafting/start",
        headers=auth_headers,
        json={"recipe_id": "farinha", "batches": 24},
    )
    assert started.status_code == 200, started.text
    moinho = next(s for s in started.json()["stations"] if s["building_id"] == "moinho")
    assert (moinho["time_bonus_bp"], moinho["yield_bonus_bp"]) == (-700, 700)

    async with session_factory() as session:
        job = (await session.scalars(select(ProductionJob))).one()
        seconds = (ensure_utc(job.finish_at) - ensure_utc(job.started_at)).total_seconds()
        assert round(seconds) == 13_392  # 600 s x 24 lotes com -7%
        assert job.output_quantity in (25, 26)  # 24 x 1,07 = 25,68


async def test_hybrid_dairy_talent_raises_the_selling_price_of_cheese(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=50, agc=3000)
    await _give(session_factory, property_id, "processed_queijo", 10)
    sell = f"/api/v1/properties/{property_id}/market/sell"

    plain = await client.post(
        sell, headers=auth_headers, json={"item_id": "processed_queijo", "quantity": 5}
    )
    assert plain.json()["gross"] == 260  # 5 x 52

    # Laticínios exige 6 pontos em Pecuária e 6 em Indústria.
    await _allocate(
        client,
        auth_headers,
        "pec_pasto_verde", "pec_cocho_farto", "pec_manejo", "pec_avicultor", "pec_leiteiro",
        "ind_ferramentas", "ind_aproveitamento", "ind_boa_receita", "ind_moleiro", "ind_padeiro",
        "hib_laticinios",
    )  # fmt: skip
    boosted = await client.post(
        sell, headers=auth_headers, json={"item_id": "processed_queijo", "quantity": 5}
    )
    assert boosted.json()["gross"] == 280  # 5 x 52 x 1,08 = 280,8

    offers = (await client.get("/api/v1/market/offers", headers=auth_headers)).json()["offers"]
    by_id = {offer["item_id"]: offer for offer in offers}
    assert by_id["processed_queijo"]["sell_bonus_bp"] == 800
    assert by_id["animal_leite"]["sell_bonus_bp"] == 800
    assert by_id["processed_pao"]["sell_bonus_bp"] == 0


async def test_hybrid_requires_points_in_both_branches(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=50)
    await _allocate(client, auth_headers, "pec_pasto_verde", "pec_cocho_farto", "pec_manejo")
    blocked = await client.post(
        "/api/v1/talents/allocate", headers=auth_headers, json={"node_id": "hib_laticinios"}
    )
    assert blocked.status_code == 422 and "pontos" in blocked.json()["detail"]
