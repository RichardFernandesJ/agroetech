"""Consultas de propriedades."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.property import Property
from app.repositories.base import BaseRepository


class PropertyRepository(BaseRepository[Property]):
    model = Property

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_owner(self, owner_id: uuid.UUID) -> Sequence[Property]:
        stmt = select(Property).where(Property.owner_id == owner_id).order_by(Property.created_at)
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_owned(self, property_id: uuid.UUID, owner_id: uuid.UUID) -> Property | None:
        stmt = select(Property).where(
            Property.id == property_id,
            Property.owner_id == owner_id,
        )
        return await self.session.scalar(stmt)

    async def get_by_id(self, property_id: uuid.UUID) -> Property | None:
        return await self.get(property_id)
