"""Fase 6: trocas diretas entre dois jogadores (custódia, aceite atômico, recusa e expiração)."""

import uuid
from datetime import timedelta

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.time import utcnow
from app.game.trade import MAX_PENDING_OUTGOING, ratio_ok, side_value, trade_fee
from app.models.trade import TradeOffer
from app.models.wallet import Wallet, WalletLedgerEntry
from tests.helpers import boost_player, inventory_quantities
from tests.test_exchange import Player, _balance, _give, _second_player

Headers = dict[str, str]
BASE = "/api/v1/trades"


def _body(**overrides):
    body = {
        "recipient": "bia_roca",
        "offer_items": [{"item_id": "crop_milho", "quantity": 10}],
        "offer_agc": 20,
        "request_items": [{"item_id": "animal_leite", "quantity": 5}],
        "request_agc": 0,
    }
    body.update(overrides)
    return body


async def _propose(client: AsyncClient, headers: Headers, key: str | None = None, **overrides):
    extra = {"Idempotency-Key": key} if key else {}
    return await client.post(BASE, headers={**headers, **extra}, json=_body(**overrides))


async def _scene(
    client: AsyncClient,
    ana: Headers,
    ana_property: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> Player:
    """Ana (nível 5, 200 AGC, 30 milhos) e Bia (nível 5, 100 AGC, 12 leites)."""
    bia = await _second_player(client, session_factory)
    await boost_player(client, ana, session_factory, level=5, agc=100)
    await boost_player(client, bia.headers, session_factory, level=5, agc=0)
    await _give(session_factory, ana_property, "crop_milho", 30)
    await _give(session_factory, bia.property_id, "animal_leite", 12)
    return bia


async def _offers(client: AsyncClient, headers: Headers) -> list[dict]:
    response = await client.get(BASE, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_value_rules_are_pure_and_consistent() -> None:
    assert side_value([("crop_milho", 10)], 20) == 70
    assert [trade_fee(v) for v in (0, 1, 45, 70, 100, 101)] == [0, 1, 1, 2, 2, 3]
    assert ratio_ok(70, 45) and ratio_ok(100, 300) and not ratio_ok(100, 301)
    assert not ratio_ok(0, 50) and not ratio_ok(50, 0)


async def test_requires_authentication_and_level(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    assert (await client.get(f"{BASE}/info")).status_code == 401
    bia = await _second_player(client, session_factory)
    await boost_player(client, bia.headers, session_factory, level=5)
    low = await _propose(client, auth_headers)  # Ana ainda no nível 1
    assert low.status_code == 422 and "nível 3" in low.json()["detail"]

    await boost_player(client, auth_headers, session_factory, level=5, agc=100)
    await _give(session_factory, property_id, "crop_milho", 10)
    # Destinatária com nível baixo: ninguém propõe a quem não pode aceitar.
    await boost_player(client, bia.headers, session_factory, level=1)
    novice = await _propose(client, auth_headers)
    assert novice.status_code == 422 and "ainda não pode negociar" in novice.json()["detail"]


async def test_info_and_player_search(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _scene(client, auth_headers, property_id, session_factory)
    info = (await client.get(f"{BASE}/info", headers=auth_headers)).json()
    assert (info["min_level"], info["fee_basis_points"], info["max_value_ratio"]) == (3, 200, 3)
    assert {"crop_milho", "animal_leite"} <= {i["item_id"] for i in info["tradable"]}

    found = (await client.get(f"{BASE}/players?q=BIA", headers=auth_headers)).json()
    assert found == [{"username": "bia_roca", "level": 5}]  # sem curingas nem a própria Ana
    assert (await client.get(f"{BASE}/players?q=%25", headers=auth_headers)).json() == []


async def test_proposal_puts_your_side_in_escrow(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    before = await _balance(client, auth_headers)

    response = await _propose(client, auth_headers)
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["direction"], body["status"], body["other_player"]) == (
        "out",
        "pending",
        "bia_roca",
    )
    assert (body["offer"]["value"], body["request"]["value"], body["your_fee"]) == (70, 45, 2)

    # 10 milhos e 20 AGC + taxa de 2 saíram da Ana.
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 20
    assert await _balance(client, auth_headers) == before - 22

    incoming = await _offers(client, bia.headers)
    assert [(o["direction"], o["status"], o["other_player"]) for o in incoming] == [
        ("in", "pending", "ana_fazendeira")
    ]
    assert incoming[0]["your_fee"] == 1  # a taxa dela é sobre o que ela entrega (45 AGC)


async def test_proposal_validation_changes_nothing(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _scene(client, auth_headers, property_id, session_factory)
    before = await _balance(client, auth_headers)

    cases = {
        "ela mesma": {"recipient": "ana_fazendeira"},
        "jogador inexistente": {"recipient": "fantasma"},
        "sem lado pedido": {"request_items": [], "request_agc": 0},
        "presente (sem valor pedido)": {"request_items": [], "request_agc": 0, "offer_agc": 50},
        "item não negociável": {"offer_items": [{"item_id": "nada", "quantity": 1}]},
        "item repetido": {
            "offer_items": [
                {"item_id": "crop_milho", "quantity": 2},
                {"item_id": "crop_milho", "quantity": 3},
            ]
        },
        "troca desigual (mais de 3x)": {
            "offer_agc": 0,
            "request_items": [{"item_id": "animal_leite", "quantity": 100}],
        },
        "estoque insuficiente": {"offer_items": [{"item_id": "crop_milho", "quantity": 31}]},
        "saldo insuficiente": {"offer_items": [], "offer_agc": 90_000, "request_agc": 100_000},
    }
    for name, overrides in cases.items():
        response = await _propose(client, auth_headers, **overrides)
        assert response.status_code in (404, 422), (name, response.status_code, response.text)

    too_many = {
        "offer_items": [
            {"item_id": i, "quantity": 1}
            for i in ("crop_milho", "seed_milho", "seed_cafe", "animal_ovo", "animal_la")
        ]
    }
    assert (await _propose(client, auth_headers, **too_many)).status_code == 422

    # Nada ficou em custódia, nem parcialmente.
    assert await _balance(client, auth_headers) == before
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 30
    assert await _offers(client, auth_headers) == []


async def test_accept_swaps_both_sides_atomically(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    ana_start, bia_start = await _balance(client, auth_headers), await _balance(client, bia.headers)
    offer_id = (await _propose(client, auth_headers)).json()["id"]

    accepted = await client.post(f"{BASE}/{offer_id}/accept", headers=bia.headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["status"] == "accepted"

    ana_items = await inventory_quantities(client, property_id, auth_headers)
    bia_items = await inventory_quantities(client, bia.property_id, bia.headers)
    assert (ana_items["crop_milho"], ana_items["animal_leite"]) == (20, 5)
    assert (bia_items["crop_milho"], bia_items["animal_leite"]) == (10, 7)
    # Ana pagou 20 AGC + taxa 2; Bia recebeu 20 AGC e pagou a taxa de 1.
    assert await _balance(client, auth_headers) == ana_start - 22
    assert await _balance(client, bia.headers) == bia_start + 20 - 1

    kinds_ana = {
        e["kind"]
        for e in (await client.get("/api/v1/wallet/ledger", headers=auth_headers)).json()["entries"]
    }
    kinds_bia = {
        e["kind"]
        for e in (await client.get("/api/v1/wallet/ledger", headers=bia.headers)).json()["entries"]
    }
    assert "trade_escrow" in kinds_ana and {"trade_paid", "trade_received"} <= kinds_bia


async def test_only_the_taxes_leave_the_economy(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    before = await _balance(client, auth_headers) + await _balance(client, bia.headers)
    offer_id = (await _propose(client, auth_headers, offer_agc=50, request_agc=10)).json()["id"]
    assert (await client.post(f"{BASE}/{offer_id}/accept", headers=bia.headers)).status_code == 200
    after = await _balance(client, auth_headers) + await _balance(client, bia.headers)
    # Ana: oferta 10 milhos + 50 AGC = 100 -> taxa 2. Bia: 5 leites + 10 AGC = 55 -> taxa 2.
    assert before - after == 4


async def test_accept_without_your_side_leaves_everything_untouched(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    offer_id = (
        await _propose(
            client,
            auth_headers,
            request_items=[{"item_id": "animal_leite", "quantity": 40}],
            offer_items=[{"item_id": "crop_milho", "quantity": 30}],
            offer_agc=100,
            request_agc=0,
        )
    ).json()["id"]
    ana_before = await _balance(client, auth_headers)

    failed = await client.post(f"{BASE}/{offer_id}/accept", headers=bia.headers)
    assert failed.status_code == 422 and "insuficiente" in failed.json()["detail"]
    pending = (await _offers(client, auth_headers))[0]
    assert pending["status"] == "pending"
    assert await _balance(client, auth_headers) == ana_before
    assert (await inventory_quantities(client, bia.property_id, bia.headers))["animal_leite"] == 12
    assert "crop_milho" not in await inventory_quantities(client, bia.property_id, bia.headers)


async def test_only_the_recipient_accepts_and_only_once(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    offer_id = (await _propose(client, auth_headers)).json()["id"]
    assert (await client.post(f"{BASE}/{offer_id}/accept", headers=auth_headers)).status_code == 404
    assert (
        await client.post(f"{BASE}/{uuid.uuid4()}/accept", headers=bia.headers)
    ).status_code == 404
    assert (await client.post(f"{BASE}/{offer_id}/accept", headers=bia.headers)).status_code == 200
    again = await client.post(f"{BASE}/{offer_id}/accept", headers=bia.headers)
    assert again.status_code == 422
    assert (await client.post(f"{BASE}/{offer_id}/cancel", headers=auth_headers)).status_code == 422


async def test_decline_and_cancel_refund_everything_including_the_fee(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    start = await _balance(client, auth_headers)

    first = (await _propose(client, auth_headers)).json()["id"]
    assert (await client.post(f"{BASE}/{first}/decline", headers=auth_headers)).status_code == 404
    declined = await client.post(f"{BASE}/{first}/decline", headers=bia.headers)
    assert declined.status_code == 200 and declined.json()["status"] == "declined"
    assert await _balance(client, auth_headers) == start
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 30

    second = (await _propose(client, auth_headers)).json()["id"]
    assert (await client.post(f"{BASE}/{second}/cancel", headers=bia.headers)).status_code == 404
    cancelled = await client.post(f"{BASE}/{second}/cancel", headers=auth_headers)
    assert cancelled.json()["status"] == "cancelled"
    assert await _balance(client, auth_headers) == start
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 30
    assert (await client.post(f"{BASE}/{second}/decline", headers=bia.headers)).status_code == 422


async def test_expired_proposals_return_the_escrow_and_cannot_be_accepted(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    start = await _balance(client, auth_headers)
    offer_id = (await _propose(client, auth_headers)).json()["id"]
    async with session_factory() as session:
        offer = await session.get(TradeOffer, uuid.UUID(offer_id))
        assert offer is not None
        offer.expires_at = utcnow() - timedelta(minutes=1)
        await session.commit()

    assert (await client.post(f"{BASE}/{offer_id}/accept", headers=bia.headers)).status_code == 422
    listed = await _offers(client, auth_headers)  # ao consultar, a custódia volta
    assert listed[0]["status"] == "expired"
    assert await _balance(client, auth_headers) == start
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 30


async def test_pending_limit_and_idempotency(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _scene(client, auth_headers, property_id, session_factory)
    small = {
        "offer_items": [{"item_id": "crop_milho", "quantity": 2}],
        "offer_agc": 0,
        "request_items": [{"item_id": "animal_leite", "quantity": 1}],
    }
    first = await _propose(client, auth_headers, key="proposta-0001", **small)
    again = await _propose(client, auth_headers, key="proposta-0001", **small)
    assert first.status_code == again.status_code == 201
    assert first.json()["id"] == again.json()["id"]
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 28
    other = await _propose(client, auth_headers, key="proposta-0001", **{**small, "offer_agc": 1})
    assert other.status_code == 409

    for _ in range(MAX_PENDING_OUTGOING - 1):
        assert (await _propose(client, auth_headers, **small)).status_code == 201
    over = await _propose(client, auth_headers, **small)
    assert over.status_code == 422 and str(MAX_PENDING_OUTGOING) in over.json()["detail"]


async def test_money_only_for_items_trade(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    await _give(session_factory, bia.property_id, "crop_milho", 10)
    ana_start, bia_start = await _balance(client, auth_headers), await _balance(client, bia.headers)
    # Ana paga 50 AGC por 10 milhos da Bia (valor 50 dos dois lados).
    offer = await _propose(
        client,
        auth_headers,
        offer_items=[],
        offer_agc=50,
        request_items=[{"item_id": "crop_milho", "quantity": 10}],
        request_agc=0,
    )
    assert offer.status_code == 201, offer.text
    assert (
        await client.post(f"{BASE}/{offer.json()['id']}/accept", headers=bia.headers)
    ).status_code == 200
    assert (await inventory_quantities(client, property_id, auth_headers))["crop_milho"] == 40
    assert await _balance(client, auth_headers) == ana_start - 50 - 1
    assert await _balance(client, bia.headers) == bia_start + 50 - 1


async def test_ledgers_reconcile_after_trades(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    bia = await _scene(client, auth_headers, property_id, session_factory)
    accepted = (await _propose(client, auth_headers)).json()["id"]
    await client.post(f"{BASE}/{accepted}/accept", headers=bia.headers)
    cancelled = (await _propose(client, auth_headers)).json()["id"]
    await client.post(f"{BASE}/{cancelled}/cancel", headers=auth_headers)
    async with session_factory() as session:
        for wallet in (await session.scalars(select(Wallet))).all():
            total = await session.scalar(
                select(func.sum(WalletLedgerEntry.amount)).where(
                    WalletLedgerEntry.wallet_id == wallet.id
                )
            )
            assert total == wallet.balance
