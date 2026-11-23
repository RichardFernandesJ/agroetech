"""Testes do inventário de sementes e produtos."""

from httpx import AsyncClient


async def test_inventory_lists_item_metadata(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    response = await client.get(
        f"/api/v1/properties/{property_id}/inventory",
        headers=auth_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["property_id"] == property_id

    items = {item["item_id"]: item for item in body["items"]}
    milho_seed = items["seed_milho"]
    assert milho_seed["name"] == "Semente de milho"
    assert milho_seed["category"] == "seed"
    assert milho_seed["quantity"] == 6


async def test_inventory_starts_without_products(
    client: AsyncClient,
    auth_headers: dict[str, str],
    property_id: str,
) -> None:
    response = await client.get(
        f"/api/v1/properties/{property_id}/inventory",
        headers=auth_headers,
    )
    item_ids = {item["item_id"] for item in response.json()["items"]}
    assert not any(item_id.startswith("crop_") for item_id in item_ids)
