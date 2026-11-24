"""Acesso a dados dos animais."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.animal import Animal
from app.repositories.base import BaseRepository


class AnimalRepository(BaseRepository[Animal]):
    model = Animal

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_by_property(
        self,
        property_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Sequence[Animal]:
        stmt = (
            select(Animal)
            .where(Animal.property_id == property_id)
            .order_by(Animal.created_at, Animal.id)
        )
        if for_update:
            # Serializa coleta/alimentação concorrentes (PostgreSQL).
            stmt = stmt.with_for_update()
        result = await self.session.scalars(stmt)
        return result.all()
