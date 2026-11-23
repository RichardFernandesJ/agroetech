"""Testes do sistema de plantação e colheita."""

from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from tests.helpers import inventory_quantities, set_planting_schedule


def _now() -> datetime:
    return datetime.now(UTC)


async def _plant(
    client: AsyncClient,
    property_id: str,
    headers: dict[str, str],
    *,
    crop_id: str = "milho",
    plot_index: int = 0,
) -> dict:
    response = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=headers,
        json={"crop_id": crop_id, "plot_index": plot_index},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_plant_consumes_seed_and_returns_growing_planting(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    planting = await _plant(client, property_id, auth_headers)

    assert planting["crop_id"] == "milho"
    assert planting["crop_name"] == "Milho"
    assert planting["plot_index"] == 0
    assert planting["status"] == "growing"
    assert planting["cycles_done"] == 0
    assert planting["stored_cycles"] == 0
    assert planting["max_cycles"] == 1
    assert planting["seconds_until_ready"] > 0

    quantities = await inventory_quantities(client, property_id, auth_headers)
    assert quantities["seed_milho"] == 5


async def test_cannot_plant_on_occupied_plot(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    await _plant(client, property_id, auth_headers)

    response = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "cenoura", "plot_index": 0},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "conflict"


async def test_cannot_plant_unknown_crop(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    response = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "abacaxi", "plot_index": 0},
    )
    assert response.status_code == 404


async def test_cannot_plant_outside_property_plots(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    response = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "milho", "plot_index": 6},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "game_rule_violation"


async def test_cannot_plant_without_seeds(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    # O kit inicial tem apenas 1 semente de café.
    await _plant(client, property_id, auth_headers, crop_id="cafe", plot_index=0)

    response = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=auth_headers,
        json={"crop_id": "cafe", "plot_index": 1},
    )
    assert response.status_code == 422
    assert "sementes" in response.json()["detail"]


async def test_cannot_harvest_before_ready(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    planting = await _plant(client, property_id, auth_headers)

    response = await client.post(
        f"/api/v1/plantings/{planting['id']}/harvest",
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "game_rule_violation"


async def test_harvest_single_cycle_crop_and_free_plot(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    planting = await _plant(client, property_id, auth_headers)
    now = _now()
    await set_planting_schedule(
        session_factory,
        planting["id"],
        next_ready_at=now - timedelta(minutes=10),
        last_sync_at=now - timedelta(minutes=15),
    )

    response = await client.post(
        f"/api/v1/plantings/{planting['id']}/harvest",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["cycles_harvested"] == 1
    assert body["product_item"] == "crop_milho"
    assert body["product_quantity"] == 3
    assert body["seed_quantity"] == 1
    assert body["planting_status"] == "exhausted"

    quantities = await inventory_quantities(client, property_id, auth_headers)
    assert quantities["crop_milho"] == 3
    assert quantities["seed_milho"] == 6  # 5 restantes + 1 semente colhida

    # O talhão volta a ficar disponível após o esgotamento.
    replanted = await _plant(client, property_id, auth_headers, plot_index=0)
    assert replanted["status"] == "growing"


async def test_tomato_regrows_before_exhausting(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    planting = await _plant(client, property_id, auth_headers, crop_id="tomate")

    first_now = _now()
    await set_planting_schedule(
        session_factory,
        planting["id"],
        next_ready_at=first_now - timedelta(minutes=20),
        last_sync_at=first_now - timedelta(minutes=25),
    )
    first_harvest = await client.post(
        f"/api/v1/plantings/{planting['id']}/harvest",
        headers=auth_headers,
    )
    assert first_harvest.status_code == 200, first_harvest.text
    first_body = first_harvest.json()
    assert first_body["cycles_harvested"] == 2
    assert first_body["product_quantity"] == 6  # 2 ciclos x 3 tomates
    assert first_body["planting_status"] == "growing"

    second_now = _now()
    await set_planting_schedule(
        session_factory,
        planting["id"],
        next_ready_at=second_now - timedelta(seconds=1),
        last_sync_at=second_now - timedelta(minutes=1),
    )
    second_harvest = await client.post(
        f"/api/v1/plantings/{planting['id']}/harvest",
        headers=auth_headers,
    )
    assert second_harvest.status_code == 200, second_harvest.text
    second_body = second_harvest.json()
    assert second_body["cycles_harvested"] == 1
    assert second_body["planting_status"] == "exhausted"

    quantities = await inventory_quantities(client, property_id, auth_headers)
    assert quantities["crop_tomate"] == 9  # 3 ciclos x 3 tomates


async def test_harvest_all_aggregates_products_and_seeds(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    milho = await _plant(client, property_id, auth_headers, plot_index=0)
    cenoura = await _plant(
        client,
        property_id,
        auth_headers,
        crop_id="cenoura",
        plot_index=1,
    )

    now = _now()
    for planting in (milho, cenoura):
        await set_planting_schedule(
            session_factory,
            planting["id"],
            next_ready_at=now - timedelta(minutes=10),
            last_sync_at=now - timedelta(minutes=15),
        )

    response = await client.post(
        f"/api/v1/properties/{property_id}/harvest",
        headers=auth_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["products"] == {"crop_milho": 3, "crop_cenoura": 4}
    assert body["seeds"] == {"seed_milho": 1, "seed_cenoura": 1}
    assert len(body["harvests"]) == 2
