"""Regras de experiência e nível."""

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.game import progression
from app.models.progress import PlayerProgress
from app.repositories.progress_repository import ProgressRepository


@dataclass(frozen=True, slots=True)
class XpGrant:
    gained: int
    previous_level: int
    info: progression.LevelInfo

    @property
    def leveled_up(self) -> bool:
        return self.info.level > self.previous_level


class ProgressService:
    def __init__(self, session: AsyncSession, progress: ProgressRepository) -> None:
        self.session = session
        self.progress = progress

    async def get_or_create(self, user_id: uuid.UUID) -> PlayerProgress:
        record = await self.progress.get_by_user_id(user_id)
        if record is not None:
            return record

        try:
            async with self.session.begin_nested():
                record = await self.progress.add(PlayerProgress(user_id=user_id, xp=0))
        except IntegrityError:
            # Outra requisição criou o registro primeiro (unique em user_id).
            record = await self.progress.get_by_user_id(user_id)
            assert record is not None
        return record

    async def describe(self, user_id: uuid.UUID) -> progression.LevelInfo:
        record = await self.get_or_create(user_id)
        return progression.describe(record.xp)

    async def grant(self, user_id: uuid.UUID, amount: int) -> XpGrant:
        """Soma XP (com trava de linha) respeitando o nível máximo."""
        if amount < 0:
            raise ValueError("O XP concedido não pode ser negativo.")

        await self.get_or_create(user_id)
        record = await self.progress.get_by_user_id(user_id, for_update=True)
        assert record is not None

        previous_level = progression.level_for_xp(record.xp)
        new_xp = min(record.xp + amount, progression.MAX_XP)
        gained = new_xp - record.xp
        record.xp = new_xp
        await self.session.flush()
        return XpGrant(
            gained=gained,
            previous_level=previous_level,
            info=progression.describe(new_xp),
        )
