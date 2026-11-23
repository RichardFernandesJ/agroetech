"""Acesso a dados da progressão do jogador."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.progress import PlayerProgress
from app.repositories.base import BaseRepository


class ProgressRepository(BaseRepository[PlayerProgress]):
    model = PlayerProgress

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> PlayerProgress | None:
        stmt = select(PlayerProgress).where(PlayerProgress.user_id == user_id)
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)
