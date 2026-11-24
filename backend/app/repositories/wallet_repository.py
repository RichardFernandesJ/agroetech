"""Acesso a dados da carteira e do livro-razão."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.wallet import Wallet, WalletLedgerEntry
from app.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    model = Wallet

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Wallet | None:
        stmt = select(Wallet).where(Wallet.user_id == user_id)
        if for_update:
            # Serializa operações concorrentes sobre o mesmo saldo (PostgreSQL).
            stmt = stmt.with_for_update()
        return await self.session.scalar(stmt)

    async def compare_and_set_balance(self, wallet: Wallet, new_balance: int) -> bool:
        """Troca o saldo só se ele ainda for o que lemos (``UPDATE ... WHERE balance = :antigo``).

        Segunda linha de defesa, independente do banco: mesmo sem trava de linha (SQLite),
        duas operações simultâneas sobre o mesmo saldo não passam as duas.
        """
        result = await self.session.execute(
            update(Wallet)
            .where(Wallet.id == wallet.id, Wallet.balance == wallet.balance)
            .values(balance=new_balance)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    async def add_entry(self, entry: WalletLedgerEntry) -> WalletLedgerEntry:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def find_entry_by_key(
        self,
        wallet_id: uuid.UUID,
        idempotency_key: str,
    ) -> WalletLedgerEntry | None:
        stmt = select(WalletLedgerEntry).where(
            WalletLedgerEntry.wallet_id == wallet_id,
            WalletLedgerEntry.idempotency_key == idempotency_key,
        )
        return await self.session.scalar(stmt)

    async def list_entries(
        self,
        wallet_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[WalletLedgerEntry]:
        stmt = (
            select(WalletLedgerEntry)
            .where(WalletLedgerEntry.wallet_id == wallet_id)
            .order_by(WalletLedgerEntry.created_at.desc(), WalletLedgerEntry.id)
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return result.all()
