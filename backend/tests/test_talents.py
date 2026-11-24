"""API de talentos: pontos, requisitos, presets, redefinição e efeitos no jogo."""

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.game import progression
from app.models.inventory import InventoryItem
from app.models.planting import Planting
from app.models.progress import PlayerProgress
from app.models.talent import TalentPreset
from tests.unit.balance import BUILDS

Headers = dict[str, str]


async def _user_id(client: AsyncClient, headers: Headers) -> uuid.UUID:
    response = await client.get("/api/v1/auth/me", headers=headers)
    return uuid.UUID(response.json()["id"])


async def _set_level(
    client: AsyncClient,
    headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
    level: int,
) -> None:
    user_id = await _user_id(client, headers)
    async with session_factory() as session:
        record = await session.scalar(
            select(PlayerProgress).where(PlayerProgress.user_id == user_id)
        )
        xp = progression.total_xp_for_level(level)
        if record is None:
            session.add(PlayerProgress(user_id=user_id, xp=xp))
        else:
            record.xp = xp
        await session.commit()


async def _allocate(client: AsyncClient, headers: Headers, node_id: str) -> dict:
    response = await client.post(
        "/api/v1/talents/allocate", headers=headers, json={"node_id": node_id}
    )
    assert response.status_code == 200, (node_id, response.text)
    return response.json()


async def _state(client: AsyncClient, headers: Headers) -> dict:
    response = await client.get("/api/v1/talents", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_talent_catalog_is_public_and_complete(client: AsyncClient) -> None:
    response = await client.get("/api/v1/catalog/talents")
    assert response.status_code == 200
    body = response.json()
    assert len(body["branches"]) == 6
    assert {b["id"] for b in body["branches"] if b["available"]} == {
        "agricultura",
        "comercio",
        "pecuaria",
        "industria",
    }
    node = next(n for n in body["nodes"] if n["id"] == "agro_solo_fertil")
    assert node["cost"] == 1 and node["tier_name"] == "Básico"
    assert node["effects"] == [{"stat": "crop_yield", "value_bp": 200, "scope": None}]


async def test_talents_require_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/talents")).status_code == 401
    assert (await client.post("/api/v1/talents/allocate", json={"node_id": "x"})).status_code == 401


async def test_new_player_has_one_active_empty_preset(
    client: AsyncClient, auth_headers: Headers
) -> None:
    state = await _state(client, auth_headers)
    assert state["level"] == 1
    assert (state["points_total"], state["points_available"]) == (0, 0)
    assert state["preset_slots"] == 1
    assert len(state["presets"]) == 1
    assert state["presets"][0]["is_active"] and state["presets"][0]["node_ids"] == []
    assert all(value == 0 for value in state["modifiers"].values())
    # Consultar de novo não cria presets extras.
    assert len((await _state(client, auth_headers))["presets"]) == 1


async def test_cannot_allocate_without_points_or_level(
    client: AsyncClient, auth_headers: Headers
) -> None:
    response = await client.post(
        "/api/v1/talents/allocate", headers=auth_headers, json={"node_id": "agro_solo_fertil"}
    )
    assert response.status_code == 422
    unknown = await client.post(
        "/api/v1/talents/allocate", headers=auth_headers, json={"node_id": "nao_existe"}
    )
    assert unknown.status_code == 404


async def test_allocate_spends_points_and_applies_modifiers(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 5)  # 4 pontos
    state = await _allocate(client, auth_headers, "agro_solo_fertil")
    assert (state["points_total"], state["points_spent"], state["points_available"]) == (4, 1, 3)
    assert state["modifiers"]["crop_yield"] == 200

    duplicate = await client.post(
        "/api/v1/talents/allocate", headers=auth_headers, json={"node_id": "agro_solo_fertil"}
    )
    assert duplicate.status_code == 409


async def test_requirements_are_enforced(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 50)
    # Camada 2 sem o pré-requisito.
    blocked = await client.post(
        "/api/v1/talents/allocate",
        headers=auth_headers,
        json={"node_id": "agro_especialista_milho"},
    )
    assert blocked.status_code == 422
    # Camada 4 sem pontos suficientes no ramo.
    blocked = await client.post(
        "/api/v1/talents/allocate", headers=auth_headers, json={"node_id": "agro_mestre_terra"}
    )
    assert blocked.status_code == 422

    await _allocate(client, auth_headers, "agro_solo_fertil")
    # A camada 2 exige 2 pontos já investidos no ramo.
    early = await client.post(
        "/api/v1/talents/allocate",
        headers=auth_headers,
        json={"node_id": "agro_especialista_milho"},
    )
    assert early.status_code == 422
    await _allocate(client, auth_headers, "agro_sementes_vigorosas")
    await _allocate(client, auth_headers, "agro_especialista_milho")


async def test_level_requirement_blocks_early_access(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 2)  # 1 ponto, mas nível 2 < 5
    await _allocate(client, auth_headers, "agro_solo_fertil")
    response = await client.post(
        "/api/v1/talents/allocate",
        headers=auth_headers,
        json={"node_id": "agro_especialista_milho"},
    )
    assert response.status_code == 422


async def test_exclusive_masters_and_full_reference_build(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 50)
    state: dict = {}
    for node_id in BUILDS["agricultor"]:
        state = await _allocate(client, auth_headers, node_id)
    assert state["points_spent"] <= state["points_total"]

    other_master = await client.post(
        "/api/v1/talents/allocate", headers=auth_headers, json={"node_id": "agro_mestre_tempo"}
    )
    assert other_master.status_code == 409
    # Os tetos do motor valem mesmo com tudo investido.
    assert state["modifiers"]["crop_yield"] <= 3_000
    assert state["modifiers"]["sell_price"] <= 4_500


async def test_presets_slots_switching_and_cooldown(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # Nível 1: só 1 espaço.
    full = await client.post(
        "/api/v1/talents/presets", headers=auth_headers, json={"name": "Extra"}
    )
    assert full.status_code == 422

    await _set_level(client, auth_headers, session_factory, 10)  # 2 espaços, 9 pontos
    created = await client.post(
        "/api/v1/talents/presets", headers=auth_headers, json={"name": "  Comerciante  "}
    )
    assert created.status_code == 201
    state = created.json()
    assert [p["name"] for p in state["presets"]] == ["Build 1", "Comerciante"]

    await _allocate(client, auth_headers, "agro_solo_fertil")
    first, second = state["presets"]

    # Primeira troca é livre; a segunda, logo em seguida, entra em recarga.
    switched = await client.post(
        f"/api/v1/talents/presets/{second['id']}/activate", headers=auth_headers
    )
    assert switched.status_code == 200
    body = switched.json()
    assert body["active_preset_id"] == second["id"]
    assert body["points_spent"] == 0
    assert body["modifiers"]["crop_yield"] == 0  # o outro preset não vale mais

    again = await client.post(
        f"/api/v1/talents/presets/{first['id']}/activate", headers=auth_headers
    )
    assert again.status_code == 422

    # Passada a recarga, a troca funciona e os bônus voltam.
    async with session_factory() as session:
        preset = await session.get(TalentPreset, uuid.UUID(second["id"]))
        assert preset is not None
        preset.last_activated_at = datetime.now(UTC) - timedelta(hours=2)
        await session.commit()
    ok = await client.post(f"/api/v1/talents/presets/{first['id']}/activate", headers=auth_headers)
    assert ok.status_code == 200
    assert ok.json()["modifiers"]["crop_yield"] == 200


async def test_rename_and_delete_presets(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 10)
    state = (
        await client.post("/api/v1/talents/presets", headers=auth_headers, json={"name": "B"})
    ).json()
    first, second = state["presets"]

    renamed = await client.patch(
        f"/api/v1/talents/presets/{second['id']}", headers=auth_headers, json={"name": "Industrial"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["presets"][1]["name"] == "Industrial"

    delete_active = await client.delete(
        f"/api/v1/talents/presets/{first['id']}", headers=auth_headers
    )
    assert delete_active.status_code == 422

    deleted = await client.delete(f"/api/v1/talents/presets/{second['id']}", headers=auth_headers)
    assert deleted.status_code == 200
    assert len(deleted.json()["presets"]) == 1


async def test_presets_of_other_players_are_not_found(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 10)
    mine = (
        await client.post("/api/v1/talents/presets", headers=auth_headers, json={"name": "B"})
    ).json()["presets"][1]

    await client.post(
        "/api/v1/auth/register",
        json={"email": "bia@agro.com.br", "username": "bia_roca", "password": "colheita2026"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"login": "bia@agro.com.br", "password": "colheita2026"}
    )
    intruder = {"Authorization": f"Bearer {login.json()['access_token']}"}

    for call in (
        client.post(f"/api/v1/talents/presets/{mine['id']}/activate", headers=intruder),
        client.delete(f"/api/v1/talents/presets/{mine['id']}", headers=intruder),
        client.patch(f"/api/v1/talents/presets/{mine['id']}", headers=intruder, json={"name": "X"}),
    ):
        assert (await call).status_code == 404


async def test_reset_first_is_free_then_costs_agc(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 10)

    nothing = await client.post("/api/v1/talents/reset", headers=auth_headers)
    assert nothing.status_code == 422  # nada a redefinir

    await _allocate(client, auth_headers, "agro_solo_fertil")
    assert (await _state(client, auth_headers))["reset_is_free"] is True
    free = await client.post("/api/v1/talents/reset", headers=auth_headers)
    assert free.status_code == 200
    assert free.json()["cost"] == 0
    assert free.json()["state"]["points_available"] == 9

    await _allocate(client, auth_headers, "agro_solo_fertil")
    state = await _state(client, auth_headers)
    assert state["reset_is_free"] is False and state["reset_cost"] == 10 * 5

    balance_before = (await client.get("/api/v1/wallet", headers=auth_headers)).json()["balance"]
    paid = await client.post("/api/v1/talents/reset", headers=auth_headers)
    assert paid.status_code == 200 and paid.json()["cost"] == 50
    balance_after = (await client.get("/api/v1/wallet", headers=auth_headers)).json()["balance"]
    assert balance_after == balance_before - 50

    ledger = (await client.get("/api/v1/wallet/ledger", headers=auth_headers)).json()
    assert ledger["entries"][0]["kind"] == "talent_respec"


async def test_reset_without_funds_changes_nothing(
    client: AsyncClient,
    auth_headers: Headers,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 50)  # custo 250 > saldo 100
    await _allocate(client, auth_headers, "agro_solo_fertil")
    assert (await client.post("/api/v1/talents/reset", headers=auth_headers)).status_code == 200
    await _allocate(client, auth_headers, "agro_solo_fertil")

    refused = await client.post("/api/v1/talents/reset", headers=auth_headers)
    assert refused.status_code == 422
    state = await _state(client, auth_headers)
    assert state["presets"][0]["node_ids"] == ["agro_solo_fertil"]
    assert (await client.get("/api/v1/wallet", headers=auth_headers)).json()["balance"] == 100


async def test_growth_modifier_is_snapshotted_at_planting(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 5)
    await _allocate(client, auth_headers, "agro_sementes_vigorosas")  # -2% de tempo

    planted = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "milho", "plot_index": 0},
    )
    assert planted.status_code == 201, planted.text
    planting_id = uuid.UUID(planted.json()["id"])

    # Redefinir os talentos depois não altera a plantação em andamento.
    assert (await client.post("/api/v1/talents/reset", headers=auth_headers)).status_code == 200

    async with session_factory() as session:
        planting = await session.get(Planting, planting_id)
        assert planting is not None
        assert planting.grow_seconds == 294  # 300 s com -2%
        assert planting.modifiers is not None
        assert planting.modifiers["crop_grow_time"] == -200
        gap = (planting.next_ready_at - planting.planted_at).total_seconds()
        assert abs(gap - 294) < 1


async def test_sell_price_and_fee_talents_change_the_payout(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _set_level(client, auth_headers, session_factory, 5)
    async with session_factory() as session:
        session.add(
            InventoryItem(property_id=uuid.UUID(property_id), item_id="crop_milho", quantity=200)
        )
        await session.commit()
    sell = f"/api/v1/properties/{property_id}/market/sell"

    plain = await client.post(
        sell, headers=auth_headers, json={"item_id": "crop_milho", "quantity": 100}
    )
    assert plain.status_code == 200
    # 100 x 5 = 500 bruto, taxa de 5% = 25.
    assert (plain.json()["gross"], plain.json()["fee"], plain.json()["amount"]) == (500, 25, 475)

    await _allocate(client, auth_headers, "com_regateio")  # +3% no preço
    await _allocate(client, auth_headers, "com_balanca_justa")  # taxa -0,5 ponto

    boosted = await client.post(
        sell, headers=auth_headers, json={"item_id": "crop_milho", "quantity": 100}
    )
    body = boosted.json()
    # 500 * 1,03 = 515; taxa de 4,5% = 23.
    assert (body["gross"], body["fee"], body["amount"]) == (515, 23, 492)

    offers = (await client.get("/api/v1/market/offers", headers=auth_headers)).json()
    assert offers["fee_basis_points"] == 450
    milho = next(o for o in offers["offers"] if o["item_id"] == "crop_milho")
    assert milho["sell_bonus_bp"] == 300
