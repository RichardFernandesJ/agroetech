"""Rotas da carteira de AgroCoin."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, WalletServiceDep
from app.game.catalog import get_item
from app.schemas.wallet import LedgerEntryRead, LedgerPage, WalletRead

router = APIRouter(prefix="/wallet", tags=["Carteira"])


@router.get("", response_model=WalletRead, summary="Saldo de AgroCoin do jogador")
async def get_wallet(current_user: CurrentUser, wallets: WalletServiceDep) -> WalletRead:
    wallet = await wallets.get_or_create(current_user.id)
    return WalletRead(id=wallet.id, balance=wallet.balance)


@router.get(
    "/ledger", response_model=LedgerPage, summary="Histórico financeiro (mais recente primeiro)"
)
async def get_ledger(
    current_user: CurrentUser,
    wallets: WalletServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> LedgerPage:
    entries = await wallets.history(current_user.id, limit=limit, offset=offset)
    rows: list[LedgerEntryRead] = []
    for entry in entries:
        definition = get_item(entry.item_id) if entry.item_id else None
        rows.append(
            LedgerEntryRead(
                id=entry.id,
                kind=entry.kind,
                amount=entry.amount,
                balance_after=entry.balance_after,
                item_id=entry.item_id,
                item_name=definition.name if definition else None,
                quantity=entry.quantity,
                unit_price=entry.unit_price,
                fee=entry.fee,
                created_at=entry.created_at,
            )
        )
    return LedgerPage(entries=rows, limit=limit, offset=offset)
