"""Rotas do mercado entre jogadores (praça)."""

import uuid
from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Header, Query, status

from app.api.deps import CurrentUser, ExchangeServiceDep
from app.game.catalog import get_item
from app.schemas.exchange import (
    BuyListingRequest,
    CreateListingRequest,
    ExchangeInfoRead,
    HistoryRead,
    ListingRead,
    PriceRead,
    TradeRead,
)
from app.services.exchange_service import HistoryView, ListingView, TradeResult

router = APIRouter(prefix="/exchange", tags=["Mercado entre jogadores"])

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Chave única por intenção; reenvios não repetem o efeito.",
    ),
]


def _name(item_id: str) -> str:
    item = get_item(item_id)
    return item.name if item else item_id


def _listing_read(view: ListingView) -> ListingRead:
    listing = view.listing
    return ListingRead(
        id=listing.id,
        seller_name=view.seller_name,
        is_mine=view.is_mine,
        item_id=listing.item_id,
        item_name=view.item_name,
        quantity_initial=listing.quantity_initial,
        quantity_remaining=listing.quantity_remaining,
        unit_price=listing.unit_price,
        status=listing.status,
        expires_at=listing.expires_at,
        created_at=listing.created_at,
    )


def _trade_read(result: TradeResult, item_name: str) -> TradeRead:
    transaction = result.transaction
    return TradeRead(
        transaction_id=transaction.id,
        listing_id=transaction.listing_id,
        item_id=transaction.item_id,
        item_name=item_name,
        quantity=transaction.quantity,
        unit_price=transaction.unit_price,
        gross=transaction.gross,
        fee=transaction.fee,
        seller_net=transaction.seller_net,
        balance=result.balance,
        listing_remaining=result.listing.quantity_remaining,
        listing_status=result.listing.status,
        replayed=result.replayed,
    )


def _history_read(view: HistoryView) -> HistoryRead:
    transaction = view.transaction
    return HistoryRead(
        id=transaction.id,
        role=view.role,
        counterpart=view.counterpart,
        item_id=transaction.item_id,
        item_name=view.item_name,
        quantity=transaction.quantity,
        unit_price=transaction.unit_price,
        gross=transaction.gross,
        fee=transaction.fee,
        amount=-transaction.gross if view.role == "buyer" else transaction.seller_net,
        created_at=transaction.created_at,
    )


@router.get("/info", response_model=ExchangeInfoRead, summary="Regras, faixas de preço e cotações")
async def get_info(current_user: CurrentUser, exchange: ExchangeServiceDep) -> ExchangeInfoRead:
    info = await exchange.info(current_user)
    return ExchangeInfoRead(
        min_level=info.min_level,
        max_active_listings=info.max_active_listings,
        listing_hours=info.listing_hours,
        fee_basis_points=info.fee_basis_points,
        player_level=info.player_level,
        active_listings=info.active_listings,
        prices=[PriceRead(**asdict(price)) for price in info.prices],
    )


@router.get("/listings", response_model=list[ListingRead], summary="Anúncios ativos")
async def browse_listings(
    current_user: CurrentUser,
    exchange: ExchangeServiceDep,
    item_id: Annotated[str | None, Query(max_length=80)] = None,
    sort: Annotated[Literal["price", "new"], Query()] = "price",
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[ListingRead]:
    views = await exchange.browse(
        current_user, item_id=item_id, newest_first=sort == "new", limit=limit, offset=offset
    )
    return [_listing_read(view) for view in views]


@router.get("/listings/mine", response_model=list[ListingRead], summary="Meus anúncios")
async def my_listings(current_user: CurrentUser, exchange: ExchangeServiceDep) -> list[ListingRead]:
    return [_listing_read(view) for view in await exchange.my_listings(current_user)]


@router.post(
    "/listings",
    response_model=ListingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Anuncia itens (ficam em custódia até vender, cancelar ou expirar)",
)
async def create_listing(
    payload: CreateListingRequest,
    current_user: CurrentUser,
    exchange: ExchangeServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> ListingRead:
    listing = await exchange.create_listing(
        current_user, payload.item_id, payload.quantity, payload.unit_price, idempotency_key
    )
    return _listing_read(ListingView(listing, current_user.username, _name(listing.item_id), True))


@router.post(
    "/listings/{listing_id}/buy",
    response_model=TradeRead,
    summary="Compra de um anúncio (parcial ou total)",
)
async def buy_listing(
    listing_id: uuid.UUID,
    payload: BuyListingRequest,
    current_user: CurrentUser,
    exchange: ExchangeServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> TradeRead:
    result = await exchange.buy(current_user, listing_id, payload.quantity, idempotency_key)
    return _trade_read(result, _name(result.transaction.item_id))


@router.delete(
    "/listings/{listing_id}",
    response_model=ListingRead,
    summary="Cancela um anúncio meu e devolve os itens restantes",
)
async def cancel_listing(
    listing_id: uuid.UUID, current_user: CurrentUser, exchange: ExchangeServiceDep
) -> ListingRead:
    listing = await exchange.cancel(current_user, listing_id)
    return _listing_read(ListingView(listing, current_user.username, _name(listing.item_id), True))


@router.get("/history", response_model=list[HistoryRead], summary="Meu histórico comercial")
async def get_history(
    current_user: CurrentUser,
    exchange: ExchangeServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[HistoryRead]:
    views = await exchange.history(current_user, limit=limit, offset=offset)
    return [_history_read(view) for view in views]
