"""Acesso a dados das construções."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.repositories.base import BaseRepository


class BuildingRepository(BaseRepository[Building]):
    model = Building

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_property(self, property_id: uuid.UUID) -> Sequence[Building]:
        stmt = select(Building).where(Building.property_id == property_id)
        result = await self.session.scalars(stmt)
        return result.all()

    async def levels_by_property(self, property_id: uuid.UUID) -> dict[str, int]:
        return {row.building_id: row.level for row in await self.list_by_property(property_id)}

    async def get_for_property(
        self,
        property_id: uuid.UUID,
        building_id: str,
        *,
        for_update: bool = False,
    ) -> Building | None:
        stmt = select(Building).where(
            Building.property_id == property_id,
            Building.building_id == building_id,
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)
