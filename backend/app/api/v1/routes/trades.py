"""Rotas das trocas diretas entre jogadores."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header, Query, status

from app.api.deps import CurrentUser, TradeServiceDep
from app.game.catalog import get_item
from app.game.exchange import reference_prices
from app.schemas.trade import (
    PlayerRead,
    ProposeRequest,
    TradableItemRead,
    TradeInfoRead,
    TradeLineRead,
    TradeOfferRead,
    TradeSideRead,
)
from app.services.trade_service import OfferView

router = APIRouter(prefix="/trades", tags=["Trocas diretas"])

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Chave única por proposta; reenvios não criam outra.",
    ),
]


def _side(items: list[tuple[str, int]], agc: int, value: int) -> TradeSideRead:
    prices = reference_prices()
    return TradeSideRead(
        items=[
            TradeLineRead(
                item_id=item_id,
                name=(get_item(item_id).name if get_item(item_id) else item_id),
                quantity=quantity,
                value=prices.get(item_id, 0) * quantity,
            )
            for item_id, quantity in items
        ],
        agc=agc,
        value=value,
    )


def _to_read(view: OfferView) -> TradeOfferRead:
    offer = view.offer
    return TradeOfferRead(
        id=offer.id,
        direction=view.direction,
        other_player=view.other_player,
        status=offer.status,
        offer=_side(view.offer_items, offer.offer_agc, view.offer_value),
        request=_side(view.request_items, offer.request_agc, view.request_value),
        your_fee=view.your_fee,
        expires_at=offer.expires_at,
        created_at=offer.created_at,
        resolved_at=offer.resolved_at,
    )


async def _read_one(
    trades: TradeServiceDep, user: CurrentUser, offer_id: uuid.UUID
) -> TradeOfferRead:
    for view in await trades.mine(user):
        if view.offer.id == offer_id:
            return _to_read(view)
    raise RuntimeError("proposta não encontrada após a operação")  # pragma: no cover


@router.get("/info", response_model=TradeInfoRead, summary="Regras das trocas e itens negociáveis")
async def get_info(current_user: CurrentUser, trades: TradeServiceDep) -> TradeInfoRead:
    info = await trades.info(current_user)
    return TradeInfoRead(
        min_level=info.min_level,
        max_pending_outgoing=info.max_pending,
        max_item_lines=info.max_lines,
        expiry_hours=info.expiry_hours,
        fee_basis_points=info.fee_basis_points,
        max_value_ratio=info.max_ratio,
        player_level=info.player_level,
        pending_outgoing=info.pending_outgoing,
        tradable=[TradableItemRead(item_id=i, name=n, value=v) for i, n, v in info.tradable],
    )


@router.get("/players", response_model=list[PlayerRead], summary="Jogadores com quem negociar")
async def search_players(
    current_user: CurrentUser,
    trades: TradeServiceDep,
    q: Annotated[str, Query(max_length=50)] = "",
) -> list[PlayerRead]:
    return [
        PlayerRead(username=p.username, level=p.level)
        for p in await trades.players(current_user, q)
    ]


@router.get("", response_model=list[TradeOfferRead], summary="Propostas enviadas e recebidas")
async def list_trades(current_user: CurrentUser, trades: TradeServiceDep) -> list[TradeOfferRead]:
    return [_to_read(view) for view in await trades.mine(current_user)]


@router.post(
    "",
    response_model=TradeOfferRead,
    status_code=status.HTTP_201_CREATED,
    summary="Propõe uma troca (o seu lado fica em custódia)",
)
async def propose(
    payload: ProposeRequest,
    current_user: CurrentUser,
    trades: TradeServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> TradeOfferRead:
    offer = await trades.propose(
        current_user,
        payload.recipient,
        [(line.item_id, line.quantity) for line in payload.offer_items],
        payload.offer_agc,
        [(line.item_id, line.quantity) for line in payload.request_items],
        payload.request_agc,
        idempotency_key,
    )
    return await _read_one(trades, current_user, offer.id)


@router.post("/{offer_id}/accept", response_model=TradeOfferRead, summary="Aceita uma proposta")
async def accept(
    offer_id: uuid.UUID, current_user: CurrentUser, trades: TradeServiceDep
) -> TradeOfferRead:
    await trades.accept(current_user, offer_id)
    return await _read_one(trades, current_user, offer_id)


@router.post("/{offer_id}/decline", response_model=TradeOfferRead, summary="Recusa uma proposta")
async def decline(
    offer_id: uuid.UUID, current_user: CurrentUser, trades: TradeServiceDep
) -> TradeOfferRead:
    await trades.decline(current_user, offer_id)
    return await _read_one(trades, current_user, offer_id)


@router.post(
    "/{offer_id}/cancel", response_model=TradeOfferRead, summary="Cancela uma proposta minha"
)
async def cancel(
    offer_id: uuid.UUID, current_user: CurrentUser, trades: TradeServiceDep
) -> TradeOfferRead:
    await trades.cancel(current_user, offer_id)
    return await _read_one(trades, current_user, offer_id)
