"""Testes de criação, leitura e posição do personagem."""

from httpx import AsyncClient

from app.game.world import SPAWN_X, SPAWN_Y, WORLD_WIDTH
from tests.helpers import inventory_quantities


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    username: str,
    password: str = "colheita2026",
) -> dict[str, str]:
    register = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    assert register.status_code == 201, register.text

    login = await client.post(
        "/api/v1/auth/login",
        json={"login": username, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


async def test_create_character_with_existing_property(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    response = await client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={
            "name": "  Ana  Maria ",
            "property_id": property_id,
            "appearance": {
                "skin_tone": "dark",
                "hair_style": "bun",
                "outfit_color": "#2f6f8f",
            },
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Ana Maria"
    assert body["property_id"] == property_id
    assert body["appearance"] == {
        "skin_tone": "dark",
        "hair_style": "bun",
        "outfit_color": "#2f6f8f",
    }
    assert body["position_x"] == SPAWN_X
    assert body["position_y"] == SPAWN_Y
    assert body["facing"] == "down"

    me = await client.get("/api/v1/characters/me", headers=auth_headers)
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


async def test_create_character_creates_starter_farm(
    client: AsyncClient,
) -> None:
    headers = await _register_and_login(
        client,
        email="bia@agro.com.br",
        username="bia_fazendeira",
    )

    response = await client.post(
        "/api/v1/characters",
        headers=headers,
        json={"name": "Bia"},
    )
    assert response.status_code == 201, response.text
    property_id = response.json()["property_id"]

    properties = await client.get("/api/v1/properties", headers=headers)
    assert properties.status_code == 200
    farms = properties.json()
    assert len(farms) == 1
    assert farms[0]["id"] == property_id
    assert farms[0]["name"] == "Fazenda de bia_fazendeira"
    assert farms[0]["plot_count"] == 6

    quantities = await inventory_quantities(client, property_id, headers)
    assert quantities["seed_milho"] == 6
    assert quantities["seed_cafe"] == 1


async def test_duplicate_character_is_rejected(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    first = await client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "Ana", "property_id": property_id},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "Outra Ana", "property_id": property_id},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


async def test_cannot_use_another_players_property(
    client: AsyncClient,
    property_id: str,
) -> None:
    other_headers = await _register_and_login(
        client,
        email="caio@agro.com.br",
        username="caio_fazendeiro",
    )

    response = await client.post(
        "/api/v1/characters",
        headers=other_headers,
        json={"name": "Caio", "property_id": property_id},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_get_character_before_creation_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    response = await client.get("/api/v1/characters/me", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


async def test_update_position_and_facing(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    await client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "Ana", "property_id": property_id},
    )

    response = await client.patch(
        "/api/v1/characters/me/position",
        headers=auth_headers,
        json={"x": 700.5, "y": 420.0, "facing": "left"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["position_x"] == 700.5
    assert body["position_y"] == 420.0
    assert body["facing"] == "left"

    me = await client.get("/api/v1/characters/me", headers=auth_headers)
    assert me.json()["position_x"] == 700.5
    assert me.json()["facing"] == "left"


async def test_update_position_rejects_out_of_bounds(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    await client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "Ana", "property_id": property_id},
    )

    response = await client.patch(
        "/api/v1/characters/me/position",
        headers=auth_headers,
        json={"x": WORLD_WIDTH, "y": 100.0, "facing": "down"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "game_rule_violation"


async def test_character_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/characters/me")
    assert response.status_code == 401

    create = await client.post("/api/v1/characters", json={"name": "Ana"})
    assert create.status_code == 401


async def test_character_validates_name_and_appearance(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    invalid_name = await client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={"name": "A", "property_id": property_id},
    )
    assert invalid_name.status_code == 422

    invalid_color = await client.post(
        "/api/v1/characters",
        headers=auth_headers,
        json={
            "name": "Ana",
            "property_id": property_id,
            "appearance": {"outfit_color": "verde"},
        },
    )
    assert invalid_color.status_code == 422
