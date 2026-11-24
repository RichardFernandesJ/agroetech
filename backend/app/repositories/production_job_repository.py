"""Acesso a dados dos trabalhos de fabricação."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.production_job import ProductionJob
from app.models.property import Property
from app.repositories.base import BaseRepository


class ProductionJobRepository(BaseRepository[ProductionJob]):
    model = ProductionJob

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def lock_property(self, property_id: uuid.UUID) -> None:
        """Serializa inícios/coletas concorrentes da mesma fazenda (PostgreSQL)."""
        await self.session.execute(
            select(Property.id).where(Property.id == property_id).with_for_update()
        )

    async def list_open(self, property_id: uuid.UUID) -> Sequence[ProductionJob]:
        """Trabalhos ainda não coletados (em andamento ou prontos)."""
        stmt = (
            select(ProductionJob)
            .where(ProductionJob.property_id == property_id, ProductionJob.collected_at.is_(None))
            .order_by(ProductionJob.finish_at, ProductionJob.id)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def find_by_key(self, property_id: uuid.UUID, key: str) -> ProductionJob | None:
        stmt = select(ProductionJob).where(
            ProductionJob.property_id == property_id,
            ProductionJob.request_key == key,
        )
        return await self.session.scalar(stmt)
