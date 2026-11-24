"""Acesso a dados das trocas diretas."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.trade import STATUS_PENDING
from app.models.trade import TradeItem, TradeOffer
from app.models.user import User
from app.repositories.base import BaseRepository


class TradeRepository(BaseRepository[TradeOffer]):
    model = TradeOffer

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_offer(
        self, offer_id: uuid.UUID, *, for_update: bool = False
    ) -> TradeOffer | None:
        stmt = select(TradeOffer).where(TradeOffer.id == offer_id)
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)

    async def find_by_key(self, proposer_id: uuid.UUID, key: str) -> TradeOffer | None:
        stmt = select(TradeOffer).where(
            TradeOffer.proposer_id == proposer_id, TradeOffer.request_key == key
        )
        return await self.session.scalar(stmt)

    async def count_pending_outgoing(self, proposer_id: uuid.UUID, now: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(TradeOffer)
            .where(
                TradeOffer.proposer_id == proposer_id,
                TradeOffer.status == STATUS_PENDING,
                TradeOffer.expires_at > now,
            )
        )
        return int(await self.session.scalar(stmt) or 0)

    async def add_items(self, items: Sequence[TradeItem]) -> None:
        self.session.add_all(items)
        await self.session.flush()

    async def items_of(self, offer_ids: Sequence[uuid.UUID]) -> Sequence[TradeItem]:
        if not offer_ids:
            return []
        stmt = (
            select(TradeItem)
            .where(TradeItem.offer_id.in_(offer_ids))
            .order_by(TradeItem.side, TradeItem.item_id)
        )
        return (await self.session.scalars(stmt)).all()

    async def list_for_user(self, user_id: uuid.UUID, limit: int = 40) -> Sequence[TradeOffer]:
        stmt = (
            select(TradeOffer)
            .where(or_(TradeOffer.proposer_id == user_id, TradeOffer.recipient_id == user_id))
            .order_by(TradeOffer.created_at.desc(), TradeOffer.id)
            .limit(limit)
        )
        return (await self.session.scalars(stmt)).all()

    async def due_for_expiry(
        self, now: datetime, *, user_id: uuid.UUID | None, limit: int
    ) -> Sequence[TradeOffer]:
        """Propostas vencidas, em ordem fixa (proponente, id) para as travas nunca se cruzarem."""
        stmt = select(TradeOffer).where(
            TradeOffer.status == STATUS_PENDING, TradeOffer.expires_at <= now
        )
        if user_id is not None:
            stmt = stmt.where(
                or_(TradeOffer.proposer_id == user_id, TradeOffer.recipient_id == user_id)
            )
        stmt = stmt.order_by(TradeOffer.proposer_id, TradeOffer.id).limit(limit)
        return (await self.session.scalars(stmt)).all()

    async def try_transition(self, offer_id: uuid.UUID, new_status: str, now: datetime) -> bool:
        """Sai de ``pending`` só uma vez (quem perde a corrida não repete a liquidação)."""
        result = await self.session.execute(
            update(TradeOffer)
            .where(TradeOffer.id == offer_id, TradeOffer.status == STATUS_PENDING)
            .values(status=new_status, resolved_at=now)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    async def search_players(self, query: str, *, exclude: uuid.UUID, limit: int) -> Sequence[User]:
        stmt = select(User).where(User.id != exclude, User.is_active.is_(True))
        if query:
            stmt = stmt.where(func.lower(User.username).startswith(query.lower(), autoescape=True))
        return (await self.session.scalars(stmt.order_by(User.username).limit(limit))).all()
