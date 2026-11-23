"""Consultas de personagens."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.character import Character
from app.repositories.base import BaseRepository


class CharacterRepository(BaseRepository[Character]):
    model = Character

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> Character | None:
        stmt = select(Character).where(Character.user_id == user_id)
        return await self.session.scalar(stmt)
