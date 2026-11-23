"""Testes de propriedades, kit inicial e isolamento entre jogadores."""

from httpx import AsyncClient

from tests.helpers import inventory_quantities


async def test_create_property_grants_starter_seeds(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    quantities = await inventory_quantities(client, property_id, auth_headers)

    assert quantities["seed_milho"] == 6
    assert quantities["seed_cenoura"] == 4
    assert quantities["seed_tomate"] == 3
    assert quantities["seed_morango"] == 2
    assert quantities["seed_cafe"] == 1


async def test_list_and_detail_properties(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    listing = await client.get("/api/v1/properties", headers=auth_headers)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [property_id]

    detail = await client.get(f"/api/v1/properties/{property_id}", headers=auth_headers)
    assert detail.status_code == 200
    assert detail.json()["name"] == "Fazenda Boa Vista"


async def test_player_cannot_access_another_players_property(
    client: AsyncClient,
    property_id: str,
) -> None:
    other = {
        "email": "bia@agro.com.br",
        "username": "bia_fazendeira",
        "password": "colheita2026",
    }
    await client.post("/api/v1/auth/register", json=other)
    login = await client.post(
        "/api/v1/auth/login",
        json={"login": other["email"], "password": other["password"]},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    detail = await client.get(f"/api/v1/properties/{property_id}", headers=other_headers)
    assert detail.status_code == 404

    inventory = await client.get(
        f"/api/v1/properties/{property_id}/inventory",
        headers=other_headers,
    )
    assert inventory.status_code == 404

    planting = await client.post(
        f"/api/v1/properties/{property_id}/plantings",
        headers=other_headers,
        json={"crop_id": "milho", "plot_index": 0},
    )
    assert planting.status_code == 404


async def test_property_respects_plot_limit(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/properties",
        headers=auth_headers,
        json={"name": "Fazenda Gigante", "area_hectares": 500, "plot_count": 13},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "game_rule_violation"


async def test_property_validates_required_fields(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.post(
        "/api/v1/properties",
        headers=auth_headers,
        json={"name": " ", "area_hectares": 0},
    )
    assert response.status_code == 422
