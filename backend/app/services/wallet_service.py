"""Regras da carteira: criação, débito/crédito atômico e histórico."""

import uuid
from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import GameRuleError
from app.game.economy import INITIAL_GRANT_AGC
from app.models.wallet import Wallet, WalletLedgerEntry
from app.repositories.wallet_repository import WalletRepository


class WalletService:
    def __init__(self, session: AsyncSession, wallets: WalletRepository) -> None:
        self.session = session
        self.wallets = wallets

    async def get_or_create(self, user_id: uuid.UUID) -> Wallet:
        """Retorna a carteira do jogador, criando-a (com o crédito inicial) se preciso."""
        wallet = await self.wallets.get_by_user_id(user_id)
        if wallet is not None:
            return wallet

        try:
            async with self.session.begin_nested():
                wallet = Wallet(user_id=user_id, balance=INITIAL_GRANT_AGC)
                await self.wallets.add(wallet)
                await self.wallets.add_entry(
                    WalletLedgerEntry(
                        wallet_id=wallet.id,
                        kind="initial_grant",
                        amount=INITIAL_GRANT_AGC,
                        balance_after=INITIAL_GRANT_AGC,
                    )
                )
        except IntegrityError:
            # Outra requisição criou a carteira primeiro (unique em user_id).
            wallet = await self.wallets.get_by_user_id(user_id)
            assert wallet is not None
        return wallet

    async def get_locked(self, user_id: uuid.UUID) -> Wallet:
        """Carteira com trava de linha, para operações que alteram o saldo."""
        await self.get_or_create(user_id)
        wallet = await self.wallets.get_by_user_id(user_id, for_update=True)
        assert wallet is not None
        return wallet

    async def apply(
        self,
        wallet: Wallet,
        *,
        kind: str,
        amount: int,
        item_id: str | None = None,
        quantity: int | None = None,
        unit_price: int | None = None,
        fee: int = 0,
        idempotency_key: str | None = None,
    ) -> WalletLedgerEntry:
        """Aplica uma variação de saldo e registra a linha do livro-razão."""
        new_balance = wallet.balance + amount
        if new_balance < 0:
            raise GameRuleError("Saldo de AgroCoin insuficiente.")

        wallet.balance = new_balance
        return await self.wallets.add_entry(
            WalletLedgerEntry(
                wallet_id=wallet.id,
                kind=kind,
                amount=amount,
                balance_after=new_balance,
                item_id=item_id,
                quantity=quantity,
                unit_price=unit_price,
                fee=fee,
                idempotency_key=idempotency_key,
            )
        )

    async def find_by_key(self, wallet: Wallet, key: str) -> WalletLedgerEntry | None:
        return await self.wallets.find_entry_by_key(wallet.id, key)

    async def history(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        offset: int,
    ) -> Sequence[WalletLedgerEntry]:
        wallet = await self.get_or_create(user_id)
        return await self.wallets.list_entries(wallet.id, limit=limit, offset=offset)
