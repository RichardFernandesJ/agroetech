"""Consultas de plantios."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.game.status import PlantingStatus
from app.models.planting import Planting
from app.models.property import Property
from app.repositories.base import BaseRepository


class PlantingRepository(BaseRepository[Planting]):
    model = Planting

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_property(
        self,
        property_id: uuid.UUID,
        *,
        include_exhausted: bool = False,
    ) -> Sequence[Planting]:
        stmt = select(Planting).where(Planting.property_id == property_id)
        if not include_exhausted:
            stmt = stmt.where(Planting.status != PlantingStatus.EXHAUSTED.value)
        stmt = stmt.order_by(Planting.plot_index, Planting.created_at)
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_active_by_property(self, property_id: uuid.UUID) -> Sequence[Planting]:
        return await self.list_by_property(property_id, include_exhausted=False)

    async def get_active_on_plot(
        self,
        property_id: uuid.UUID,
        plot_index: int,
    ) -> Planting | None:
        stmt = select(Planting).where(
            Planting.property_id == property_id,
            Planting.plot_index == plot_index,
            Planting.status != PlantingStatus.EXHAUSTED.value,
        )
        return await self.session.scalar(stmt)

    async def get_owned(
        self,
        planting_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Planting | None:
        stmt = (
            select(Planting)
            .join(Property, Planting.property_id == Property.id)
            .where(
                Planting.id == planting_id,
                Property.owner_id == owner_id,
            )
            .options(selectinload(Planting.property))
        )
        return await self.session.scalar(stmt)
