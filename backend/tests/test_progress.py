"""Fase de progressão: curva de XP, nível e concessão por plantio/colheita."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.game import progression
from app.game.catalog import CROPS
from tests.helpers import set_planting_schedule

Headers = dict[str, str]


async def _progress(client: AsyncClient, headers: Headers) -> dict:
    response = await client.get("/api/v1/progress", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _plant(client: AsyncClient, property_id: str, headers: Headers, plot: int = 0) -> dict:
    response = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=headers,
        json={"crop_id": "milho", "plot_index": plot},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _make_ready(session_factory: async_sessionmaker[AsyncSession], planting_id: str) -> None:
    now = datetime.now(UTC)
    await set_planting_schedule(
        session_factory,
        planting_id,
        next_ready_at=now - timedelta(minutes=10),
        last_sync_at=now - timedelta(minutes=15),
    )


def test_level_curve_is_monotonic_and_capped() -> None:
    assert progression.level_for_xp(0) == 1
    assert progression.level_for_xp(49) == 1
    assert progression.level_for_xp(50) == 2
    previous = 0
    for level in range(1, progression.MAX_LEVEL + 1):
        total = progression.total_xp_for_level(level)
        assert total >= previous
        assert progression.level_for_xp(total) == level
        previous = total
    assert progression.level_for_xp(10**12) == progression.MAX_LEVEL


def test_describe_reports_progress_inside_level() -> None:
    info = progression.describe(60)
    assert (info.level, info.xp_into_level, info.xp_for_next) == (2, 10, 100)
    top = progression.describe(progression.MAX_XP)
    assert top.level == progression.MAX_LEVEL
    assert top.xp_for_next is None


def test_every_crop_awards_harvest_xp() -> None:
    assert all(crop.harvest_xp > 0 for crop in CROPS.values())


async def test_progress_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/progress")).status_code == 401


async def test_new_player_starts_at_level_one(client: AsyncClient, auth_headers: Headers) -> None:
    body = await _progress(client, auth_headers)
    assert body["level"] == 1
    assert body["xp"] == 0
    assert body["xp_for_next"] == 50
    assert body["max_level"] == progression.MAX_LEVEL


async def test_planting_grants_xp(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    await _plant(client, property_id, auth_headers)
    assert (await _progress(client, auth_headers))["xp"] == progression.PLANT_XP


async def test_failed_planting_grants_no_xp(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    await _plant(client, property_id, auth_headers)
    duplicate = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "milho", "plot_index": 0},
    )
    assert duplicate.status_code == 409
    assert (await _progress(client, auth_headers))["xp"] == progression.PLANT_XP


async def test_harvest_grants_xp_once(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    planting = await _plant(client, property_id, auth_headers)
    await _make_ready(session_factory, planting["id"])

    first = await client.post(f"/api/v1/plantings/{planting['id']}/harvest", headers=auth_headers)
    assert first.status_code == 200, first.text
    expected = CROPS["milho"].harvest_xp
    assert first.json()["xp_gained"] == expected

    # Colher de novo não concede XP (não há mais ciclos armazenados).
    second = await client.post(f"/api/v1/plantings/{planting['id']}/harvest", headers=auth_headers)
    assert second.status_code == 422

    assert (await _progress(client, auth_headers))["xp"] == progression.PLANT_XP + expected


async def test_harvest_all_sums_xp(
    client: AsyncClient,
    auth_headers: Headers,
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    for plot in range(3):
        planting = await _plant(client, property_id, auth_headers, plot)
        await _make_ready(session_factory, planting["id"])

    response = await client.post(f"/api/v1/properties/{property_id}/harvest", headers=auth_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["harvests"]) == 3
    assert body["xp_gained"] == 3 * CROPS["milho"].harvest_xp
    assert (await _progress(client, auth_headers))["xp"] == (
        3 * progression.PLANT_XP + body["xp_gained"]
    )


async def test_xp_is_per_player(
    client: AsyncClient, auth_headers: Headers, property_id: str
) -> None:
    await _plant(client, property_id, auth_headers)
    await client.post(
        "/api/v1/auth/register",
        json={"email": "bia@agro.com.br", "username": "bia_roca", "password": "colheita2026"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"login": "bia@agro.com.br", "password": "colheita2026"}
    )
    other = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await _progress(client, other))["xp"] == 0
