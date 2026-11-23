"""Consultas e mutações de inventário."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem
from app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[InventoryItem]):
    model = InventoryItem

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_property(self, property_id: uuid.UUID) -> Sequence[InventoryItem]:
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.property_id == property_id)
            .order_by(InventoryItem.item_id)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_item(
        self,
        property_id: uuid.UUID,
        item_id: str,
    ) -> InventoryItem | None:
        stmt = select(InventoryItem).where(
            InventoryItem.property_id == property_id,
            InventoryItem.item_id == item_id,
        )
        return await self.session.scalar(stmt)

    async def get_item_for_update(
        self,
        property_id: uuid.UUID,
        item_id: str,
    ) -> InventoryItem | None:
        """Trava a linha no PostgreSQL para evitar perda de atualização.

        No SQLite o ``FOR UPDATE`` é ignorado, o que é aceitável para os testes.
        """
        stmt = (
            select(InventoryItem)
            .where(
                InventoryItem.property_id == property_id,
                InventoryItem.item_id == item_id,
            )
            .with_for_update()
        )
        return await self.session.scalar(stmt)

    async def add_quantity(
        self,
        property_id: uuid.UUID,
        item_id: str,
        amount: int,
    ) -> InventoryItem:
        item = await self.get_item(property_id, item_id)
        if item is None:
            item = InventoryItem(
                property_id=property_id,
                item_id=item_id,
                quantity=max(0, amount),
            )
            return await self.add(item)

        item.quantity += amount
        await self.session.flush()
        return item
