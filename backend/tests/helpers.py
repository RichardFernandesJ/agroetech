"""Helpers para preparar cenários de tempo e ler o estado via API."""

import uuid
from datetime import datetime

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.planting import Planting
from app.models.property import Property


async def set_planting_schedule(
    session_factory: async_sessionmaker[AsyncSession],
    planting_id: str,
    *,
    next_ready_at: datetime,
    last_sync_at: datetime,
) -> None:
    """Ajusta o relógio do plantio e da fazenda para simular tempo decorrido."""
    async with session_factory() as session:
        planting = await session.get(Planting, uuid.UUID(planting_id))
        assert planting is not None, "Plantio não encontrado no banco de teste."
        planting.next_ready_at = next_ready_at

        property_ = await session.get(Property, planting.property_id)
        assert property_ is not None
        property_.last_production_sync_at = last_sync_at
        await session.commit()


async def set_property_last_sync(
    session_factory: async_sessionmaker[AsyncSession],
    property_id: str,
    *,
    last_sync_at: datetime,
) -> None:
    async with session_factory() as session:
        property_ = await session.get(Property, uuid.UUID(property_id))
        assert property_ is not None
        property_.last_production_sync_at = last_sync_at
        await session.commit()


async def inventory_quantities(
    client: AsyncClient,
    property_id: str,
    headers: dict[str, str],
) -> dict[str, int]:
    response = await client.get(
        f"/api/v1/properties/{property_id}/inventory",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return {row["item_id"]: row["quantity"] for row in response.json()["items"]}


async def boost_player(
    client: AsyncClient,
    headers: dict[str, str],
    session_factory: async_sessionmaker[AsyncSession],
    *,
    level: int,
    agc: int = 0,
) -> None:
    """Define o nível do jogador e credita AGC (com linha no ledger, para conciliar)."""
    from sqlalchemy import select

    from app.game import progression
    from app.models.progress import PlayerProgress
    from app.models.wallet import Wallet, WalletLedgerEntry

    await client.get("/api/v1/wallet", headers=headers)  # cria a carteira
    me = await client.get("/api/v1/auth/me", headers=headers)
    user_id = uuid.UUID(me.json()["id"])
    async with session_factory() as session:
        progress = await session.scalar(
            select(PlayerProgress).where(PlayerProgress.user_id == user_id)
        )
        xp = progression.total_xp_for_level(level)
        if progress is None:
            session.add(PlayerProgress(user_id=user_id, xp=xp))
        else:
            progress.xp = xp
        if agc:
            wallet = await session.scalar(select(Wallet).where(Wallet.user_id == user_id))
            assert wallet is not None
            wallet.balance += agc
            session.add(
                WalletLedgerEntry(
                    wallet_id=wallet.id,
                    kind="test_grant",
                    amount=agc,
                    balance_after=wallet.balance,
                )
            )
        await session.commit()
