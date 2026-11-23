"""Acesso a dados de talentos."""

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.talent import PresetNode, TalentPreset, TalentRespec
from app.repositories.base import BaseRepository


class TalentRepository(BaseRepository[TalentPreset]):
    model = TalentPreset

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def list_presets(self, user_id: uuid.UUID) -> Sequence[TalentPreset]:
        stmt = (
            select(TalentPreset)
            .where(TalentPreset.user_id == user_id)
            .options(selectinload(TalentPreset.nodes))
            .order_by(TalentPreset.slot)
            .execution_options(populate_existing=True)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_preset(self, user_id: uuid.UUID, preset_id: uuid.UUID) -> TalentPreset | None:
        stmt = (
            select(TalentPreset)
            .where(TalentPreset.id == preset_id, TalentPreset.user_id == user_id)
            .options(selectinload(TalentPreset.nodes))
            .execution_options(populate_existing=True)
        )
        return await self.session.scalar(stmt)

    async def get_active(
        self, user_id: uuid.UUID, *, for_update: bool = False
    ) -> TalentPreset | None:
        stmt = (
            select(TalentPreset)
            .where(TalentPreset.user_id == user_id, TalentPreset.is_active.is_(True))
            .options(selectinload(TalentPreset.nodes))
            .execution_options(populate_existing=True)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)

    async def add_node(self, preset_id: uuid.UUID, node_id: str) -> PresetNode:
        node = PresetNode(preset_id=preset_id, node_id=node_id)
        self.session.add(node)
        await self.session.flush()
        return node

    async def clear_nodes(self, preset_id: uuid.UUID) -> int:
        count = await self.session.scalar(
            select(func.count()).select_from(PresetNode).where(PresetNode.preset_id == preset_id)
        )
        await self.session.execute(delete(PresetNode).where(PresetNode.preset_id == preset_id))
        await self.session.flush()
        return int(count or 0)

    async def count_respecs(self, user_id: uuid.UUID) -> int:
        count = await self.session.scalar(
            select(func.count()).select_from(TalentRespec).where(TalentRespec.user_id == user_id)
        )
        return int(count or 0)

    async def add_respec(self, respec: TalentRespec) -> TalentRespec:
        self.session.add(respec)
        await self.session.flush()
        return respec
