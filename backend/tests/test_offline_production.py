"""Testes da produção offline com teto de tempo e de ciclos."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from tests.helpers import inventory_quantities, set_planting_schedule


def _now() -> datetime:
    return datetime.now(UTC)


async def _plant_cafe(
    client: AsyncClient,
    property_id: str,
    headers: dict[str, str],
) -> dict:
    response = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=headers,
        json={"crop_id": "cafe", "plot_index": 0},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _sync(
    client: AsyncClient,
    property_id: str,
    headers: dict[str, str],
) -> dict:
    response = await client.post(
        f"/api/v1/properties/{property_id}/production/sync",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_sync_without_plantings_is_a_no_op(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    body = await _sync(client, property_id, auth_headers)

    assert body["plantings_synced"] == 0
    assert body["cycles_stored"] == 0
    assert body["ready_plantings"] == 0
    assert body["offline_seconds"] >= 0


async def test_offline_sync_stores_cycles_but_does_not_collect_them(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    planting = await _plant_cafe(client, property_id, auth_headers)
    now = _now()
    await set_planting_schedule(
        session_factory,
        planting["id"],
        next_ready_at=now - timedelta(hours=20),
        last_sync_at=now - timedelta(hours=30),
    )

    body = await _sync(client, property_id, auth_headers)

    # Café: 1h por ciclo, 6 colheitas no total. As 12h de janela permitem
    # armazenar mais ciclos do que a cultura suporta, então o teto é 6.
    assert body["plantings_synced"] == 1
    assert body["cycles_stored"] == 6
    assert body["ready_plantings"] == 1
    assert body["offline_seconds"] >= 30 * 3600 - 60

    # Produção offline apenas armazena: o inventário só muda na colheita.
    quantities = await inventory_quantities(client, property_id, auth_headers)
    assert quantities.get("crop_cafe", 0) == 0

    harvest = await client.post(
        f"/api/v1/properties/{property_id}/harvest",
        headers=auth_headers,
    )
    assert harvest.status_code == 200, harvest.text
    harvest_body = harvest.json()
    assert harvest_body["products"] == {"crop_cafe": 48}  # 6 ciclos x 8
    assert harvest_body["seeds"] == {"seed_cafe": 6}


async def test_offline_window_discards_cycles_older_than_cap(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "offline_max_hours", 2)

    planting = await _plant_cafe(client, property_id, auth_headers)
    now = _now()
    await set_planting_schedule(
        session_factory,
        planting["id"],
        next_ready_at=now - timedelta(hours=20),
        last_sync_at=now - timedelta(hours=30),
    )

    body = await _sync(client, property_id, auth_headers)

    # Com janela de 2h e ciclo de 1h, apenas 2 ciclos (agora e 1h atrás)
    # estão dentro da janela; os outros 19 foram perdidos.
    assert body["cycles_stored"] == 2
    assert body["ready_plantings"] == 1


async def test_offline_sync_respects_stored_cycles_cap_and_is_idempotent(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "offline_max_cycles_per_planting", 2)

    planting = await _plant_cafe(client, property_id, auth_headers)
    now = _now()
    await set_planting_schedule(
        session_factory,
        planting["id"],
        next_ready_at=now - timedelta(hours=20),
        last_sync_at=now - timedelta(hours=30),
    )

    first = await _sync(client, property_id, auth_headers)
    assert first["cycles_stored"] == 2
    assert first["ready_plantings"] == 1

    # Sincronizar novamente não duplica ciclos já armazenados.
    second = await _sync(client, property_id, auth_headers)
    assert second["cycles_stored"] == 0
    assert second["ready_plantings"] == 1


async def test_sync_requires_authentication(
    client: AsyncClient,
    property_id: str,
) -> None:
    response = await client.post(f"/api/v1/properties/{property_id}/production/sync")
    assert response.status_code == 401
