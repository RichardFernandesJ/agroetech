"""Acesso a dados do mercado entre jogadores."""

import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.game.exchange import STATUS_ACTIVE, STATUS_SOLD
from app.models.exchange import MarketListing, MarketTransaction
from app.models.property import Property
from app.models.user import User
from app.repositories.base import BaseRepository


class ExchangeRepository(BaseRepository[MarketListing]):
    model = MarketListing

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ------------------------------------------------------------- anúncios
    async def get_listing(
        self, listing_id: uuid.UUID, *, for_update: bool = False
    ) -> MarketListing | None:
        stmt = select(MarketListing).where(MarketListing.id == listing_id)
        if for_update:
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)

    async def find_by_key(self, seller_id: uuid.UUID, key: str) -> MarketListing | None:
        stmt = select(MarketListing).where(
            MarketListing.seller_id == seller_id, MarketListing.request_key == key
        )
        return await self.session.scalar(stmt)

    async def lock_seller_property(self, property_id: uuid.UUID) -> None:
        """Serializa as criações de anúncio da mesma fazenda (o limite não pode ser furado)."""
        await self.session.execute(
            select(Property.id).where(Property.id == property_id).with_for_update()
        )

    async def count_active(self, seller_id: uuid.UUID, now: datetime) -> int:
        stmt = (
            select(func.count())
            .select_from(MarketListing)
            .where(
                MarketListing.seller_id == seller_id,
                MarketListing.status == STATUS_ACTIVE,
                MarketListing.expires_at > now,
            )
        )
        return int(await self.session.scalar(stmt) or 0)

    async def browse(
        self,
        now: datetime,
        *,
        item_id: str | None,
        newest_first: bool,
        limit: int,
        offset: int,
    ) -> Sequence[tuple[MarketListing, str]]:
        stmt = (
            select(MarketListing, User.username)
            .join(User, User.id == MarketListing.seller_id)
            .where(MarketListing.status == STATUS_ACTIVE, MarketListing.expires_at > now)
        )
        if item_id:
            stmt = stmt.where(MarketListing.item_id == item_id)
        order = (
            (MarketListing.created_at.desc(), MarketListing.id)
            if newest_first
            else (MarketListing.unit_price, MarketListing.created_at, MarketListing.id)
        )
        result = await self.session.execute(stmt.order_by(*order).limit(limit).offset(offset))
        return [(row[0], row[1]) for row in result.all()]

    async def list_by_seller(
        self, seller_id: uuid.UUID, limit: int = 40
    ) -> Sequence[MarketListing]:
        stmt = (
            select(MarketListing)
            .where(MarketListing.seller_id == seller_id)
            .order_by(MarketListing.created_at.desc(), MarketListing.id)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def due_for_expiry(
        self, now: datetime, *, seller_id: uuid.UUID | None, limit: int
    ) -> Sequence[MarketListing]:
        stmt = select(MarketListing).where(
            MarketListing.status == STATUS_ACTIVE, MarketListing.expires_at <= now
        )
        if seller_id is not None:
            stmt = stmt.where(MarketListing.seller_id == seller_id)
        result = await self.session.scalars(stmt.order_by(MarketListing.expires_at).limit(limit))
        return result.all()

    async def try_close(self, listing_id: uuid.UUID, new_status: str) -> bool:
        """Encerra o anúncio só se ainda ativo (quem perde a corrida não devolve de novo)."""
        result = await self.session.execute(
            update(MarketListing)
            .where(MarketListing.id == listing_id, MarketListing.status == STATUS_ACTIVE)
            .values(status=new_status)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    async def try_take(self, listing_id: uuid.UUID, quantity: int, now: datetime) -> bool:
        """Retira unidades do anúncio só se ainda houver (``WHERE quantity_remaining >= :n``)."""
        result = await self.session.execute(
            update(MarketListing)
            .where(
                MarketListing.id == listing_id,
                MarketListing.status == STATUS_ACTIVE,
                MarketListing.expires_at > now,
                MarketListing.quantity_remaining >= quantity,
            )
            .values(quantity_remaining=MarketListing.quantity_remaining - quantity)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            return False
        await self.session.execute(
            update(MarketListing)
            .where(MarketListing.id == listing_id, MarketListing.quantity_remaining == 0)
            .values(status=STATUS_SOLD)
            .execution_options(synchronize_session=False)
        )
        return True

    # ------------------------------------------------------------ transações
    async def add_transaction(self, transaction: MarketTransaction) -> MarketTransaction:
        self.session.add(transaction)
        await self.session.flush()
        return transaction

    async def find_transaction_by_key(
        self, buyer_id: uuid.UUID, key: str
    ) -> MarketTransaction | None:
        stmt = select(MarketTransaction).where(
            MarketTransaction.buyer_id == buyer_id, MarketTransaction.request_key == key
        )
        return await self.session.scalar(stmt)

    async def history(
        self, user_id: uuid.UUID, *, limit: int, offset: int
    ) -> Sequence[MarketTransaction]:
        stmt = (
            select(MarketTransaction)
            .where(
                or_(MarketTransaction.buyer_id == user_id, MarketTransaction.seller_id == user_id)
            )
            .order_by(MarketTransaction.created_at.desc(), MarketTransaction.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def recent_prices(self, item_id: str, limit: int = 10) -> list[int]:
        stmt = (
            select(MarketTransaction.unit_price)
            .where(MarketTransaction.item_id == item_id)
            .order_by(MarketTransaction.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.scalars(stmt)).all())

    async def lowest_listing(self, item_id: str, now: datetime) -> int | None:
        stmt = select(func.min(MarketListing.unit_price)).where(
            MarketListing.item_id == item_id,
            MarketListing.status == STATUS_ACTIVE,
            MarketListing.expires_at > now,
        )
        return await self.session.scalar(stmt)
