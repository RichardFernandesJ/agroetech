"""Fase 4: carteira AgroCoin, compra de sementes e venda de safras."""

import uuid

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.game.economy import INITIAL_GRANT_AGC, sale_fee
from app.models.inventory import InventoryItem
from app.models.wallet import Wallet, WalletLedgerEntry
from tests.helpers import inventory_quantities

Headers = dict[str, str]


async def _balance(client: AsyncClient, headers: Headers) -> int:
    response = await client.get("/api/v1/wallet", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["balance"]


async def _give(
    session_factory: async_sessionmaker[AsyncSession],
    property_id: str,
    item_id: str,
    quantity: int,
) -> None:
    async with session_factory() as session:
        session.add(
            InventoryItem(property_id=uuid.UUID(property_id), item_id=item_id, quantity=quantity)
        )
        await session.commit()


async def test_wallet_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/wallet")).status_code == 401
    assert (await client.get("/api/v1/market/offers")).status_code == 401


async def test_wallet_starts_with_initial_grant_once(
    client: AsyncClient, auth_headers: Headers
) -> None:
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC

    ledger = (await client.get("/api/v1/wallet/ledger", headers=auth_headers)).json()
    assert [row["kind"] for row in ledger["entries"]] == ["initial_grant"]
    assert ledger["entries"][0]["balance_after"] == INITIAL_GRANT_AGC


async def test_offers_use_server_side_prices(client: AsyncClient, auth_headers: Headers) -> None:
    response = await client.get("/api/v1/market/offers", headers=auth_headers)
    assert response.status_code == 200
    offers = {row["item_id"]: row for row in response.json()["offers"]}
    assert offers["seed_milho"]["buy_price"] == 8
    assert offers["seed_milho"]["sell_price"] is None
    assert offers["crop_milho"]["sell_price"] == 5
    assert offers["crop_milho"]["buy_price"] is None


async def test_buy_seeds_debits_wallet_and_credits_inventory(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    before = (await inventory_quantities(client, property_id, auth_headers))["seed_milho"]

    response = await client.post(
        f"/api/v1/properties/{property_id}/market/buy",
        headers=auth_headers,
        json={"item_id": "seed_milho", "quantity": 5},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["amount"] == -40
    assert body["balance"] == INITIAL_GRANT_AGC - 40
    assert body["replayed"] is False

    after = (await inventory_quantities(client, property_id, auth_headers))["seed_milho"]
    assert after == before + 5
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC - 40


async def test_buy_rejects_insufficient_balance_without_side_effects(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    before = await inventory_quantities(client, property_id, auth_headers)

    response = await client.post(
        f"/api/v1/properties/{property_id}/market/buy",
        headers=auth_headers,
        json={"item_id": "seed_cafe", "quantity": 2},  # 180 AGC > 100
    )
    assert response.status_code == 422
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC
    assert await inventory_quantities(client, property_id, auth_headers) == before


async def test_buy_rejects_items_not_for_sale_and_invalid_quantity(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    url = f"/api/v1/properties/{property_id}/market/buy"
    for payload in (
        {"item_id": "crop_milho", "quantity": 1},
        {"item_id": "item_inexistente", "quantity": 1},
    ):
        assert (await client.post(url, headers=auth_headers, json=payload)).status_code == 422
    for quantity in (0, -3, 100000):
        response = await client.post(
            url, headers=auth_headers, json={"item_id": "seed_milho", "quantity": quantity}
        )
        assert response.status_code == 422
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC


async def test_sell_crops_applies_fee_and_consumes_inventory(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _give(session_factory, property_id, "crop_milho", 10)

    response = await client.post(
        f"/api/v1/properties/{property_id}/market/sell",
        headers=auth_headers,
        json={"item_id": "crop_milho", "quantity": 10},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    gross = 10 * 5
    fee = sale_fee(gross)
    assert (body["gross"], body["fee"], body["amount"]) == (gross, fee, gross - fee)
    assert fee > 0
    assert body["balance"] == INITIAL_GRANT_AGC + gross - fee

    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 0


async def test_sell_rejects_more_than_owned_and_seeds(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _give(session_factory, property_id, "crop_milho", 2)
    url = f"/api/v1/properties/{property_id}/market/sell"

    too_many = await client.post(
        url, headers=auth_headers, json={"item_id": "crop_milho", "quantity": 3}
    )
    assert too_many.status_code == 422
    seeds = await client.post(
        url, headers=auth_headers, json={"item_id": "seed_milho", "quantity": 1}
    )
    assert seeds.status_code == 422

    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 2
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC


async def test_idempotency_key_prevents_double_purchase(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    url = f"/api/v1/properties/{property_id}/market/buy"
    headers = {**auth_headers, "Idempotency-Key": "compra-0001-abcd"}
    payload = {"item_id": "seed_milho", "quantity": 2}

    first = await client.post(url, headers=headers, json=payload)
    second = await client.post(url, headers=headers, json=payload)

    assert first.status_code == second.status_code == 200
    assert first.json()["replayed"] is False
    assert second.json()["replayed"] is True
    assert first.json()["balance"] == second.json()["balance"] == INITIAL_GRANT_AGC - 16
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC - 16


async def test_idempotency_key_reused_for_other_operation_conflicts(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    url = f"/api/v1/properties/{property_id}/market/buy"
    headers = {**auth_headers, "Idempotency-Key": "compra-0002-abcd"}

    await client.post(url, headers=headers, json={"item_id": "seed_milho", "quantity": 1})
    conflict = await client.post(
        url, headers=headers, json={"item_id": "seed_milho", "quantity": 4}
    )
    assert conflict.status_code == 409
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC - 8


async def test_invalid_idempotency_key_is_rejected(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    response = await client.post(
        f"/api/v1/properties/{property_id}/market/buy",
        headers={**auth_headers, "Idempotency-Key": "curta"},
        json={"item_id": "seed_milho", "quantity": 1},
    )
    assert response.status_code == 422


async def test_trading_in_another_players_property_is_not_found(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    other = await client.post(
        "/api/v1/auth/register",
        json={"email": "bia@agro.com.br", "username": "bia_roca", "password": "colheita2026"},
    )
    assert other.status_code == 201
    login = await client.post(
        "/api/v1/auth/login", json={"login": "bia@agro.com.br", "password": "colheita2026"}
    )
    intruder = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await client.post(
        f"/api/v1/properties/{property_id}/market/buy",
        headers=intruder,
        json={"item_id": "seed_milho", "quantity": 1},
    )
    assert response.status_code == 404
    assert await _balance(client, intruder) == INITIAL_GRANT_AGC


async def test_ledger_reconciles_with_balance(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _give(session_factory, property_id, "crop_cenoura", 6)
    base = f"/api/v1/properties/{property_id}/market"
    await client.post(
        f"{base}/buy", headers=auth_headers, json={"item_id": "seed_tomate", "quantity": 3}
    )
    await client.post(
        f"{base}/sell", headers=auth_headers, json={"item_id": "crop_cenoura", "quantity": 6}
    )
    await client.post(
        f"{base}/buy", headers=auth_headers, json={"item_id": "seed_cafe", "quantity": 99}
    )

    balance = await _balance(client, auth_headers)
    async with session_factory() as session:
        total = await session.scalar(select(func.sum(WalletLedgerEntry.amount)))
        stored = await session.scalar(select(Wallet.balance))
    assert total == stored == balance

    page = (await client.get("/api/v1/wallet/ledger?limit=2", headers=auth_headers)).json()
    assert len(page["entries"]) == 2
    assert page["entries"][0]["balance_after"] == balance


async def test_balance_never_goes_negative(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    url = f"/api/v1/properties/{property_id}/market/buy"
    payload = {"item_id": "seed_cafe", "quantity": 1}  # 90 AGC cada

    assert (await client.post(url, headers=auth_headers, json=payload)).status_code == 200
    assert (await client.post(url, headers=auth_headers, json=payload)).status_code == 422
    assert await _balance(client, auth_headers) == INITIAL_GRANT_AGC - 90
