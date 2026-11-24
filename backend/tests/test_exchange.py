"""Fase 6: mercado entre jogadores (custódia, compra, taxa, expiração e histórico)."""

import uuid
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.time import utcnow
from app.game.exchange import MAX_ACTIVE_LISTINGS, price_bounds
from app.models.exchange import MarketListing
from app.models.inventory import InventoryItem
from app.models.wallet import Wallet, WalletLedgerEntry
from tests.helpers import boost_player, inventory_quantities

Headers = dict[str, str]
BASE = "/api/v1/exchange"


class Player:
    def __init__(self, headers: Headers, property_id: str) -> None:
        self.headers = headers
        self.property_id = property_id


async def _second_player(
    client: AsyncClient, session_factory: async_sessionmaker[AsyncSession]
) -> Player:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bia@agro.com.br", "username": "bia_roca", "password": "colheita2026"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"login": "bia@agro.com.br", "password": "colheita2026"}
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    created = await client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Fazenda da Bia", "area_hectares": 8, "plot_count": 6},
    )
    assert created.status_code == 201, created.text
    return Player(headers, created.json()["id"])


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


async def _balance(client: AsyncClient, headers: Headers) -> int:
    return (await client.get("/api/v1/wallet", headers=headers)).json()["balance"]


async def _list(
    client: AsyncClient,
    headers: Headers,
    item: str = "crop_milho",
    quantity: int = 10,
    price: int = 6,
    key: str | None = None,
):
    extra = {"Idempotency-Key": key} if key else {}
    return await client.post(
        f"{BASE}/listings",
        headers={**headers, **extra},
        json={"item_id": item, "quantity": quantity, "unit_price": price},
    )


async def _buy(
    client: AsyncClient,
    headers: Headers,
    listing_id: str,
    quantity: int,
    key: str | None = None,
):
    extra = {"Idempotency-Key": key} if key else {}
    return await client.post(
        f"{BASE}/listings/{listing_id}/buy",
        headers={**headers, **extra},
        json={"quantity": quantity},
    )


async def _market(
    client: AsyncClient,
    seller_headers: Headers,
    seller_property: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[Player, str]:
    """Vendedora (Bia) com 10 milhos anunciados a 6 AGC e comprador (Ana) rico o bastante."""
    buyer_headers = seller_headers
    bia = await _second_player(client, session_factory)
    await boost_player(client, bia.headers, session_factory, level=5, agc=0)
    await boost_player(client, buyer_headers, session_factory, level=5, agc=500)
    await _give(session_factory, bia.property_id, "crop_milho", 40)
    created = await _list(client, bia.headers)
    assert created.status_code == 201, created.text
    return bia, created.json()["id"]


async def test_requires_authentication_and_level(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert (await client.get(f"{BASE}/info")).status_code == 401
    assert (await client.get(f"{BASE}/listings")).status_code == 401
    await _give(session_factory, property_id, "crop_milho", 10)
    low = await _list(client, auth_headers)
    assert low.status_code == 422 and "nível 3" in low.json()["detail"]


async def test_info_exposes_rules_and_price_bands(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=4)
    info = (await client.get(f"{BASE}/info", headers=auth_headers)).json()
    assert (info["min_level"], info["fee_basis_points"], info["player_level"]) == (3, 500, 4)
    assert info["max_active_listings"] == MAX_ACTIVE_LISTINGS
    prices = {p["item_id"]: p for p in info["prices"]}
    assert (prices["crop_milho"]["minimum"], prices["crop_milho"]["maximum"]) == (3, 15)
    assert prices["seed_milho"]["reference"] == 8
    assert prices["processed_queijo"]["maximum"] == 156  # 52 x 3
    assert price_bounds("crop_milho") == (3, 5, 15) and price_bounds("nada") is None


async def test_listing_puts_items_in_escrow_and_validates(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=5)
    await _give(session_factory, property_id, "crop_milho", 10)

    ok = await _list(client, auth_headers, quantity=4, price=6)
    assert ok.status_code == 201, ok.text
    body = ok.json()
    assert (body["quantity_remaining"], body["status"], body["is_mine"]) == (4, "active", True)
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 6

    assert (await _list(client, auth_headers, price=2)).status_code == 422  # abaixo de 50%
    assert (await _list(client, auth_headers, price=16)).status_code == 422  # acima de 300%
    assert (await _list(client, auth_headers, item="nada")).status_code == 422
    assert (
        await _list(client, auth_headers, item="seed_cafe", price=90)
    ).status_code == 422  # sem estoque
    assert (await _list(client, auth_headers, quantity=7)).status_code == 422  # só restam 6
    assert (await _list(client, auth_headers, quantity=0)).status_code == 422
    assert (await _list(client, auth_headers, quantity=1000)).status_code == 422
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 6


async def test_listing_is_idempotent(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=5)
    await _give(session_factory, property_id, "crop_milho", 10)
    first = await _list(client, auth_headers, quantity=3, key="anuncio-0001")
    second = await _list(client, auth_headers, quantity=3, key="anuncio-0001")
    assert first.status_code == 201 and second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 7
    conflict = await _list(client, auth_headers, quantity=4, key="anuncio-0001")
    assert conflict.status_code == 409


async def test_active_listing_limit(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await boost_player(client, auth_headers, session_factory, level=5)
    await _give(session_factory, property_id, "crop_milho", MAX_ACTIVE_LISTINGS + 5)
    for _ in range(MAX_ACTIVE_LISTINGS):
        assert (await _list(client, auth_headers, quantity=1)).status_code == 201
    over = await _list(client, auth_headers, quantity=1)
    assert over.status_code == 422 and str(MAX_ACTIVE_LISTINGS) in over.json()["detail"]
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 5


async def test_browse_sorts_filters_and_marks_own_listings(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _second_player(client, session_factory)
    for headers in (auth_headers, bia.headers):
        await boost_player(client, headers, session_factory, level=5)
    await _give(session_factory, property_id, "crop_milho", 10)
    await _give(session_factory, bia.property_id, "crop_milho", 10)
    await _give(session_factory, bia.property_id, "animal_ovo", 10)
    await _list(client, auth_headers, quantity=2, price=9)
    await _list(client, bia.headers, quantity=2, price=4)
    await _list(client, bia.headers, item="animal_ovo", quantity=2, price=6)

    milho = (await client.get(f"{BASE}/listings?item_id=crop_milho", headers=auth_headers)).json()
    assert [row["unit_price"] for row in milho] == [4, 9]  # mais barato primeiro
    assert [row["is_mine"] for row in milho] == [False, True]
    assert milho[0]["seller_name"] == "bia_roca" and milho[0]["item_name"] == "Milho"

    everything = (await client.get(f"{BASE}/listings?sort=new", headers=auth_headers)).json()
    assert len(everything) == 3
    page = (await client.get(f"{BASE}/listings?limit=1&offset=1", headers=auth_headers)).json()
    assert len(page) == 1

    mine = (await client.get(f"{BASE}/listings/mine", headers=auth_headers)).json()
    assert [row["unit_price"] for row in mine] == [9]


async def test_purchase_moves_items_money_fee_and_history(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia, listing_id = await _market(client, auth_headers, property_id, session_factory)
    ana_before, bia_before = (
        await _balance(client, auth_headers),
        await _balance(client, bia.headers),
    )

    response = await _buy(client, auth_headers, listing_id, 10)
    assert response.status_code == 200, response.text
    body = response.json()
    # 10 x 6 = 60 AGC; taxa de 5% = 3 (sai da economia); a vendedora recebe 57.
    assert (body["gross"], body["fee"], body["seller_net"]) == (60, 3, 57)
    assert (body["listing_remaining"], body["listing_status"]) == (0, "sold")
    assert await _balance(client, auth_headers) == ana_before - 60 == body["balance"]
    assert await _balance(client, bia.headers) == bia_before + 57

    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 10
    assert (await inventory_quantities(client, bia.property_id, bia.headers))["crop_milho"] == 30

    buyer_history = (await client.get(f"{BASE}/history", headers=auth_headers)).json()
    seller_history = (await client.get(f"{BASE}/history", headers=bia.headers)).json()
    assert (buyer_history[0]["role"], buyer_history[0]["amount"]) == ("buyer", -60)
    assert (seller_history[0]["role"], seller_history[0]["amount"]) == ("seller", 57)
    assert buyer_history[0]["counterpart"] == "bia_roca"

    buyer_ledger = (await client.get("/api/v1/wallet/ledger", headers=auth_headers)).json()
    seller_ledger = (await client.get("/api/v1/wallet/ledger", headers=bia.headers)).json()
    assert buyer_ledger["entries"][0]["kind"] == "p2p_purchase"
    assert (seller_ledger["entries"][0]["kind"], seller_ledger["entries"][0]["fee"]) == (
        "p2p_sale",
        3,
    )


async def test_money_and_items_are_conserved_except_the_fee(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia, listing_id = await _market(client, auth_headers, property_id, session_factory)

    async def total_milho() -> int:
        """Milho em inventários + em custódia nos anúncios (tem de ser constante)."""
        async with session_factory() as session:
            escrow = await session.scalar(select(func.sum(MarketListing.quantity_remaining)))
        in_inventories = 0
        for player_property, headers in (
            (property_id, auth_headers),
            (bia.property_id, bia.headers),
        ):
            stock = await inventory_quantities(client, player_property, headers)
            in_inventories += stock.get("crop_milho", 0)
        return in_inventories + int(escrow or 0)

    total_before = await _balance(client, auth_headers) + await _balance(client, bia.headers)
    items_before = await total_milho()

    assert (
        await _buy(client, auth_headers, listing_id, 7)
    ).status_code == 200  # taxa: 42 x 5% = 2,1 arredonda para 3

    total_after = await _balance(client, auth_headers) + await _balance(client, bia.headers)
    assert total_before - total_after == 3  # só a taxa saiu da economia (42 x 5% = 2,1 -> 3)
    assert await total_milho() == items_before == 40  # nenhum item criado ou perdido


async def test_partial_purchases_until_sold_out(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, listing_id = await _market(client, auth_headers, property_id, session_factory)
    first = await _buy(client, auth_headers, listing_id, 4)
    assert (first.json()["listing_remaining"], first.json()["listing_status"]) == (6, "active")
    too_many = await _buy(client, auth_headers, listing_id, 7)
    assert too_many.status_code == 422 and "6" in too_many.json()["detail"]
    last = await _buy(client, auth_headers, listing_id, 6)
    assert last.json()["listing_status"] == "sold"
    again = await _buy(client, auth_headers, listing_id, 1)
    assert again.status_code == 422


async def test_cannot_buy_own_listing_or_without_funds_or_unknown(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia, listing_id = await _market(client, auth_headers, property_id, session_factory)
    own = await _buy(client, bia.headers, listing_id, 1)
    assert own.status_code == 422 and "próprio" in own.json()["detail"]
    assert (await _buy(client, auth_headers, str(uuid.uuid4()), 1)).status_code == 404

    # Sem saldo: nada muda (nem estoque do anúncio, nem inventário, nem carteira da vendedora).
    async with session_factory() as session:
        wallet = await session.scalar(
            select(Wallet).where(Wallet.balance == await _balance(client, auth_headers))
        )
        assert wallet is not None
        wallet.balance = 10
        await session.commit()
    poor = await _buy(client, auth_headers, listing_id, 10)
    assert poor.status_code == 422 and "Saldo" in poor.json()["detail"]
    listing = (await client.get(f"{BASE}/listings", headers=auth_headers)).json()[0]
    assert listing["quantity_remaining"] == 10
    assert await _balance(client, bia.headers) == 100
    assert "crop_milho" not in await inventory_quantities(client, property_id, auth_headers)


async def test_purchase_is_idempotent(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    _, listing_id = await _market(client, auth_headers, property_id, session_factory)
    before = await _balance(client, auth_headers)
    first = await _buy(client, auth_headers, listing_id, 3, key="compra-p2p-001")
    second = await _buy(client, auth_headers, listing_id, 3, key="compra-p2p-001")
    assert first.status_code == second.status_code == 200
    assert first.json()["replayed"] is False and second.json()["replayed"] is True
    assert first.json()["transaction_id"] == second.json()["transaction_id"]
    assert await _balance(client, auth_headers) == before - 18  # cobrou uma vez só
    conflict = await _buy(client, auth_headers, listing_id, 4, key="compra-p2p-001")
    assert conflict.status_code == 409


async def test_fee_rounds_up_so_tiny_purchases_cannot_dodge_it(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    from app.game.exchange import p2p_fee

    assert [p2p_fee(g, 500) for g in (0, 1, 6, 19, 20, 21, 60, 200)] == [0, 1, 1, 1, 1, 2, 3, 10]
    assert p2p_fee(200, 450) == 9 and p2p_fee(10, 100) == 1

    bia, listing_id = await _market(client, auth_headers, property_id, session_factory)
    one = await _buy(client, auth_headers, listing_id, 1)  # 6 AGC: antes pagaria taxa 0
    assert (one.json()["gross"], one.json()["fee"], one.json()["seller_net"]) == (6, 1, 5)


async def test_cancel_returns_remaining_items(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia, listing_id = await _market(client, auth_headers, property_id, session_factory)
    await _buy(client, auth_headers, listing_id, 4)
    assert (await inventory_quantities(client, bia.property_id, bia.headers))["crop_milho"] == 30

    stranger = await client.delete(f"{BASE}/listings/{listing_id}", headers=auth_headers)
    assert stranger.status_code == 404  # só a vendedora cancela

    cancelled = await client.delete(f"{BASE}/listings/{listing_id}", headers=bia.headers)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert (await inventory_quantities(client, bia.property_id, bia.headers))["crop_milho"] == 36
    assert (
        await client.delete(f"{BASE}/listings/{listing_id}", headers=bia.headers)
    ).status_code == 422
    assert (await _buy(client, auth_headers, listing_id, 1)).status_code == 422


async def test_expired_listings_return_items_and_cannot_be_bought(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia, listing_id = await _market(client, auth_headers, property_id, session_factory)
    async with session_factory() as session:
        listing = await session.get(MarketListing, uuid.UUID(listing_id))
        assert listing is not None
        listing.expires_at = utcnow() - timedelta(minutes=1)
        await session.commit()

    assert (await _buy(client, auth_headers, listing_id, 1)).status_code == 422
    # Navegar na praça devolve os itens vencidos ao vendedor (sem processo em segundo plano).
    assert (await client.get(f"{BASE}/listings", headers=auth_headers)).json() == []
    assert (await inventory_quantities(client, bia.property_id, bia.headers))["crop_milho"] == 40
    mine = (await client.get(f"{BASE}/listings/mine", headers=bia.headers)).json()
    assert [row["status"] for row in mine] == ["expired"]


async def test_seller_talents_reduce_the_fee(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _second_player(client, session_factory)
    await boost_player(client, bia.headers, session_factory, level=10)
    await boost_player(client, auth_headers, session_factory, level=5, agc=1000)
    allocate = await client.post(
        "/api/v1/talents/allocate", headers=bia.headers, json={"node_id": "com_balanca_justa"}
    )
    assert allocate.status_code == 200  # taxa de venda 0,5 ponto menor
    await _give(session_factory, bia.property_id, "processed_queijo", 10)
    listing = await _list(client, bia.headers, item="processed_queijo", quantity=4, price=50)
    info = (await client.get(f"{BASE}/info", headers=bia.headers)).json()
    assert info["fee_basis_points"] == 450

    bought = await _buy(client, auth_headers, listing.json()["id"], 4)
    assert (bought.json()["gross"], bought.json()["fee"]) == (200, 9)  # 4,5% de 200


async def test_ledgers_reconcile_for_both_players(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia, listing_id = await _market(client, auth_headers, property_id, session_factory)
    await _buy(client, auth_headers, listing_id, 5)
    async with session_factory() as session:
        for wallet in (await session.scalars(select(Wallet))).all():
            total = await session.scalar(
                select(func.sum(WalletLedgerEntry.amount)).where(
                    WalletLedgerEntry.wallet_id == wallet.id
                )
            )
            assert total == wallet.balance
