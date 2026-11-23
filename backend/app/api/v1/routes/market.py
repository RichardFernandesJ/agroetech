"""Rotas do entreposto NPC (compra de sementes e venda de safras)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import CurrentUser, MarketServiceDep, TalentServiceDep
from app.game.catalog import ITEM_CATALOG, crop_id_for_item, get_item
from app.game.economy import SALE_FEE_BASIS_POINTS, product_prices, seed_prices
from app.game.modifiers import Stat, effective_fee_bp
from app.schemas.market import MarketOffersRead, OfferRead, TradeRead, TradeRequest
from app.services.market_service import TradeResult

router = APIRouter(tags=["Mercado"])

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Chave única por intenção de compra/venda; reenvios não repetem o efeito.",
    ),
]


def _to_trade_read(result: TradeResult) -> TradeRead:
    entry = result.entry
    definition = get_item(entry.item_id or "")
    quantity = entry.quantity or 0
    unit_price = entry.unit_price or 0
    return TradeRead(
        kind=entry.kind,
        item_id=entry.item_id or "",
        item_name=definition.name if definition else (entry.item_id or ""),
        quantity=quantity,
        unit_price=unit_price,
        # Venda: bruto = líquido + taxa. Compra: bruto = valor debitado.
        gross=entry.amount + entry.fee if entry.amount > 0 else -entry.amount,
        fee=entry.fee,
        amount=entry.amount,
        balance=result.balance,
        replayed=result.replayed,
    )


@router.get(
    "/market/offers",
    response_model=MarketOffersRead,
    summary="Preços de compra e venda do entreposto",
)
async def list_offers(
    current_user: CurrentUser,
    talents: TalentServiceDep,
) -> MarketOffersRead:
    buy = seed_prices()
    sell = product_prices()
    modifiers = await talents.modifiers_for(current_user.id)
    offers = [
        OfferRead(
            item_id=item.id,
            name=item.name,
            category=item.category,
            buy_price=buy.get(item.id),
            sell_price=sell.get(item.id),
            sell_bonus_bp=(
                modifiers.total_bp(Stat.SELL_PRICE, crop_id_for_item(item.id))
                if item.id in sell
                else 0
            ),
        )
        for item in ITEM_CATALOG.values()
        if item.id in buy or item.id in sell
    ]
    fee_bp = effective_fee_bp(SALE_FEE_BASIS_POINTS, modifiers.total_bp(Stat.MARKET_FEE))
    return MarketOffersRead(fee_basis_points=fee_bp, offers=offers)


@router.post(
    "/properties/{property_id}/market/buy",
    response_model=TradeRead,
    summary="Compra sementes com AgroCoin",
)
async def buy(
    property_id: uuid.UUID,
    payload: TradeRequest,
    current_user: CurrentUser,
    market: MarketServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> TradeRead:
    result = await market.buy_seeds(
        current_user, property_id, payload.item_id, payload.quantity, idempotency_key
    )
    return _to_trade_read(result)


@router.post(
    "/properties/{property_id}/market/sell",
    response_model=TradeRead,
    summary="Vende safras do inventário por AgroCoin (com taxa)",
)
async def sell(
    property_id: uuid.UUID,
    payload: TradeRequest,
    current_user: CurrentUser,
    market: MarketServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> TradeRead:
    result = await market.sell_products(
        current_user, property_id, payload.item_id, payload.quantity, idempotency_key
    )
    return _to_trade_read(result)
