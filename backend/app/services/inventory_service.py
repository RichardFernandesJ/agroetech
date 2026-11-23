"""Regras de inventário."""

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import GameRuleError
from app.models.inventory import InventoryItem
from app.repositories.inventory_repository import InventoryRepository


class InventoryService:
    def __init__(self, session: AsyncSession, inventory: InventoryRepository) -> None:
        self.session = session
        self.inventory = inventory

    async def list_items(self, property_id: uuid.UUID) -> Sequence[InventoryItem]:
        return await self.inventory.list_by_property(property_id)

    async def add(self, property_id: uuid.UUID, item_id: str, quantity: int) -> InventoryItem:
        if quantity < 0:
            raise ValueError("A quantidade a adicionar não pode ser negativa.")
        return await self.inventory.add_quantity(property_id, item_id, quantity)

    async def consume(
        self,
        property_id: uuid.UUID,
        item_id: str,
        quantity: int,
        *,
        label: str,
    ) -> InventoryItem:
        item = await self.inventory.get_item_for_update(property_id, item_id)
        if item is None or item.quantity < quantity:
            raise GameRuleError(f"Quantidade insuficiente de {label} no inventário.")

        item.quantity -= quantity
        await self.session.flush()
        return item
