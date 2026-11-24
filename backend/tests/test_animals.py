"""Fase 5: animais (compra, abrigo, alimentação, produção offline e coleta)."""

import uuid
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.time import ensure_utc
from app.models.animal import Animal
from app.models.inventory import InventoryItem
from app.models.wallet import Wallet, WalletLedgerEntry
from tests.helpers import boost_player, inventory_quantities

Headers = dict[str, str]


def _url(property_id: str, tail: str = "") -> str:
    return f"/api/v1/properties/{property_id}/animals{tail}"


async def _state(client: AsyncClient, headers: Headers, property_id: str) -> dict:
    response = await client.get(_url(property_id), headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _build(
    client: AsyncClient, headers: Headers, property_id: str, building: str, times: int = 1
) -> None:
    for _ in range(times):
        response = await client.post(
            f"/api/v1/properties/{property_id}/buildings/{building}/upgrade", headers=headers
        )
        assert response.status_code == 200, response.text


async def _buy(
    client: AsyncClient,
    headers: Headers,
    property_id: str,
    species: str = "galinha",
    key: str | None = None,
):
    extra = {"Idempotency-Key": key} if key else {}
    return await client.post(
        _url(property_id, "/buy"), headers={**headers, **extra}, json={"species": species}
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


async def _shift_time(session_factory: async_sessionmaker[AsyncSession], hours: float) -> None:
    """Volta o relógio dos animais: simula ``hours`` horas passadas (offline)."""
    async with session_factory() as session:
        for animal in (await session.scalars(select(Animal))).all():
            delta = timedelta(hours=hours)
            animal.last_sync_at = ensure_utc(animal.last_sync_at) - delta
            if animal.fed_until is not None:
                animal.fed_until = ensure_utc(animal.fed_until) - delta
        await session.commit()


async def _balance(client: AsyncClient, headers: Headers) -> int:
    return (await client.get("/api/v1/wallet", headers=headers)).json()["balance"]


async def _ready_farm(
    client: AsyncClient,
    headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    level: int = 10,
    agc: int = 2000,
) -> None:
    await boost_player(client, headers, session_factory, level=level, agc=agc)
    await _build(client, headers, property_id, "galinheiro")


async def test_requires_authentication(client: AsyncClient, property_id: str) -> None:
    assert (await client.get(_url(property_id))).status_code == 401
    assert (await client.post(_url(property_id, "/collect"))).status_code == 401


async def test_initial_state_explains_what_is_missing(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    state = await _state(client, auth_headers, property_id)
    assert state["animals"] == []
    assert {s["id"] for s in state["species"]} == {"galinha", "vaca", "ovelha"}
    galinha = next(s for s in state["species"] if s["id"] == "galinha")
    assert galinha["can_buy"] is False and galinha["price"] == 60
    assert {h["building_id"]: h["capacity"] for h in state["housings"]} == {
        "galinheiro": 0,
        "estabulo": 0,
    }


async def test_buy_requires_level_housing_funds_and_capacity(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Nível 1: bloqueado.
    low = await _buy(client, auth_headers, property_id)
    assert low.status_code == 422 and "nível de jogador 2" in low.json()["detail"]

    # Sem galinheiro.
    await boost_player(client, auth_headers, session_factory, level=10, agc=2000)
    none = await _buy(client, auth_headers, property_id)
    assert none.status_code == 422 and "Galinheiro" in none.json()["detail"]

    # Com galinheiro nível 1 (3 vagas): a 4ª compra falha por lotação.
    await _build(client, auth_headers, property_id, "galinheiro")
    for _ in range(3):
        assert (await _buy(client, auth_headers, property_id)).status_code == 200
    full = await _buy(client, auth_headers, property_id)
    assert full.status_code == 422 and "lotado" in full.json()["detail"]
    # Melhorar o galinheiro (6 vagas) libera a compra.
    await _build(client, auth_headers, property_id, "galinheiro")
    assert (await _buy(client, auth_headers, property_id)).status_code == 200


async def test_buy_charges_and_rejects_without_funds(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory, agc=0)
    # saldo 100, galinheiro custou 80 -> sobram 20
    assert await _balance(client, auth_headers) == 20
    poor = await _buy(client, auth_headers, property_id)
    assert poor.status_code == 422 and "Saldo insuficiente" in poor.json()["detail"]
    assert (await _state(client, auth_headers, property_id))["animals"] == []

    await boost_player(client, auth_headers, session_factory, level=10, agc=100)
    ok = await _buy(client, auth_headers, property_id)
    assert ok.status_code == 200
    assert len(ok.json()["animals"]) == 1
    assert await _balance(client, auth_headers) == 120 - 60


async def test_unknown_species_and_foreign_property(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    assert (await _buy(client, auth_headers, property_id, "dragao")).status_code == 404

    await client.post(
        "/api/v1/auth/register",
        json={"email": "bia@agro.com.br", "username": "bia_roca", "password": "colheita2026"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"login": "bia@agro.com.br", "password": "colheita2026"}
    )
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.get(_url(property_id), headers=other)).status_code == 404
    assert (await _buy(client, other, property_id)).status_code == 404
    assert (await client.post(_url(property_id, "/collect"), headers=other)).status_code == 404


async def test_buy_is_idempotent(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    before = await _balance(client, auth_headers)
    first = await _buy(client, auth_headers, property_id, key="compra-animal-01")
    second = await _buy(client, auth_headers, property_id, key="compra-animal-01")
    assert first.json()["replayed"] is False and second.json()["replayed"] is True
    assert len(second.json()["animals"]) == 1
    assert await _balance(client, auth_headers) == before - 60
    conflict = await _buy(client, auth_headers, property_id, "vaca", key="compra-animal-01")
    assert conflict.status_code == 409


async def test_feeding_consumes_feed_and_caps_at_the_buffer(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    animal_id = (await _buy(client, auth_headers, property_id)).json()["animals"][0]["id"]

    # Sem ração no inventário.
    none = await client.post(
        _url(property_id, f"/{animal_id}/feed"), headers=auth_headers, json={"units": 1}
    )
    assert none.status_code == 422 and "ração" in none.json()["detail"]

    await _give(session_factory, property_id, "crop_milho", 30)
    fed = await client.post(
        _url(property_id, f"/{animal_id}/feed"), headers=auth_headers, json={"units": 2}
    )
    assert fed.status_code == 200, fed.text
    assert fed.json()["units_fed"] == {"crop_milho": 2}
    animal = fed.json()["animals"][0]
    assert animal["is_fed"] and 3500 < animal["fed_seconds_left"] <= 3600
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 28

    # Pede muito: só entram as porções até o teto de 8 h (16 porções no total).
    big = await client.post(
        _url(property_id, f"/{animal_id}/feed"), headers=auth_headers, json={"units": 64}
    )
    assert big.status_code == 200
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 28 - 14

    full = await client.post(
        _url(property_id, f"/{animal_id}/feed"), headers=auth_headers, json={"units": 1}
    )
    assert full.status_code == 422 and "máximo" in full.json()["detail"]
    missing = await client.post(
        _url(property_id, f"/{uuid.uuid4()}/feed"), headers=auth_headers, json={"units": 1}
    )
    assert missing.status_code == 404


async def test_offline_production_is_deterministic_and_collectable(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    animal_id = (await _buy(client, auth_headers, property_id)).json()["animals"][0]["id"]
    await _give(session_factory, property_id, "crop_milho", 10)
    await client.post(
        _url(property_id, f"/{animal_id}/feed"), headers=auth_headers, json={"units": 4}
    )  # 2 h

    # Passam 2 h: 2 h alimentada / 15 min = 8 ovos.
    await _shift_time(session_factory, 2)
    state = await _state(client, auth_headers, property_id)
    assert state["animals"][0]["stored"] == 8
    assert (await _state(client, auth_headers, property_id))["animals"][0]["stored"] == 8  # estável

    collected = await client.post(_url(property_id, "/collect"), headers=auth_headers)
    assert collected.status_code == 200, collected.text
    body = collected.json()
    assert body["products"] == {"animal_ovo": 8} and body["xp_gained"] == 8
    assert body["animals"][0]["stored"] == 0
    assert (await inventory_quantities(client, property_id, auth_headers))["animal_ovo"] == 8

    again = await client.post(_url(property_id, "/collect"), headers=auth_headers)
    assert again.status_code == 422
    progress = (await client.get("/api/v1/progress", headers=auth_headers)).json()
    assert progress["xp"] >= 8


async def test_hunger_stops_production(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    animal_id = (await _buy(client, auth_headers, property_id)).json()["animals"][0]["id"]
    await _give(session_factory, property_id, "crop_milho", 5)
    await client.post(
        _url(property_id, f"/{animal_id}/feed"), headers=auth_headers, json={"units": 2}
    )  # 1 h

    await _shift_time(session_factory, 5)  # 5 h depois: só a 1ª hora produziu
    animal = (await _state(client, auth_headers, property_id))["animals"][0]
    assert animal["stored"] == 4 and animal["is_fed"] is False
    assert animal["seconds_to_next"] is None


async def test_feed_all_shares_the_inventory(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    for _ in range(2):
        await _buy(client, auth_headers, property_id)
    await _give(session_factory, property_id, "crop_milho", 3)

    response = await client.post(
        _url(property_id, "/feed-all"), headers=auth_headers, json={"units": 2}
    )
    assert response.status_code == 200, response.text
    # 3 milhos para 2 galinhas que pediram 2 cada: a 1ª recebe 2, a 2ª recebe 1.
    assert response.json()["units_fed"] == {"crop_milho": 3}
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 0
    assert all(a["is_fed"] for a in response.json()["animals"])


async def test_feed_all_without_animals(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    response = await client.post(
        _url(property_id, "/feed-all"), headers=auth_headers, json={"units": 1}
    )
    assert response.status_code == 422


async def test_products_sell_at_the_market_with_fee(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    await _give(session_factory, property_id, "animal_ovo", 10)
    before = await _balance(client, auth_headers)

    response = await client.post(
        f"/api/v1/properties/{property_id}/market/sell",
        headers=auth_headers,
        json={"item_id": "animal_ovo", "quantity": 10},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["gross"], body["fee"], body["amount"]) == (40, 2, 38)
    assert await _balance(client, auth_headers) == before + 38

    offers = (await client.get("/api/v1/market/offers", headers=auth_headers)).json()["offers"]
    assert {"animal_ovo", "animal_leite", "animal_la"} <= {o["item_id"] for o in offers}


async def test_ledger_reconciles_after_animal_purchases(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _ready_farm(client, auth_headers, property_id, session_factory)
    await _buy(client, auth_headers, property_id)
    async with session_factory() as session:
        total = await session.scalar(select(func.sum(WalletLedgerEntry.amount)))
        stored = await session.scalar(select(Wallet.balance))
    assert total == stored == await _balance(client, auth_headers)
    kinds = {
        e["kind"]
        for e in (await client.get("/api/v1/wallet/ledger", headers=auth_headers)).json()["entries"]
    }
    assert "animal_purchase" in kinds


async def test_stable_houses_cows_and_sheep_together(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=10, agc=3000)
    await _build(client, auth_headers, property_id, "estabulo")  # 2 vagas, compartilhadas
    assert (await _buy(client, auth_headers, property_id, "vaca")).status_code == 200
    assert (await _buy(client, auth_headers, property_id, "ovelha")).status_code == 200
    full = await _buy(client, auth_headers, property_id, "vaca")
    assert full.status_code == 422 and "lotado" in full.json()["detail"]
    state = await _state(client, auth_headers, property_id)
    stable = next(h for h in state["housings"] if h["building_id"] == "estabulo")
    assert (stable["used"], stable["capacity"]) == (2, 2)
