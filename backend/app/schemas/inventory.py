"""Schemas de inventário."""

import uuid

from pydantic import BaseModel


class InventoryItemRead(BaseModel):
    item_id: str
    name: str
    category: str
    description: str
    quantity: int


class InventoryRead(BaseModel):
    property_id: uuid.UUID
    items: list[InventoryItemRead]
