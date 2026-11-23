"""Rotas de inventário."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, InventoryServiceDep, PropertyServiceDep
from app.api.v1.serializers import serialize_inventory
from app.schemas.inventory import InventoryRead

router = APIRouter(prefix="/properties/{property_id}/inventory", tags=["Inventário"])


@router.get(
    "",
    response_model=InventoryRead,
    summary="Lista sementes e produtos da propriedade",
)
async def get_inventory(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    properties: PropertyServiceDep,
    inventory: InventoryServiceDep,
) -> InventoryRead:
    await properties.get_owned(property_id, current_user.id)
    items = await inventory.list_items(property_id)
    return serialize_inventory(property_id, items)
