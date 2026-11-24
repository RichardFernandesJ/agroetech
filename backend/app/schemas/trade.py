"""Schemas das trocas diretas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.game.trade import MAX_AGC, MAX_ITEM_LINES, MAX_ITEM_QUANTITY


class TradeLineIn(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=MAX_ITEM_QUANTITY)


class ProposeRequest(BaseModel):
    recipient: str = Field(
        min_length=1, max_length=50, description="Nome de usuário do destinatário"
    )
    offer_items: list[TradeLineIn] = Field(default_factory=list, max_length=MAX_ITEM_LINES)
    offer_agc: int = Field(default=0, ge=0, le=MAX_AGC)
    request_items: list[TradeLineIn] = Field(default_factory=list, max_length=MAX_ITEM_LINES)
    request_agc: int = Field(default=0, ge=0, le=MAX_AGC)


class TradeLineRead(BaseModel):
    item_id: str
    name: str
    quantity: int
    value: int


class TradeSideRead(BaseModel):
    items: list[TradeLineRead]
    agc: int
    # Valor de referência do lado (itens pelo preço do entreposto + AGC).
    value: int


class TradeOfferRead(BaseModel):
    id: uuid.UUID
    direction: str  # "in" (recebida) | "out" (enviada)
    other_player: str
    status: str
    offer: TradeSideRead
    request: TradeSideRead
    # Taxa que ESTE jogador paga (proponente: já cobrada; destinatário: cobrada ao aceitar).
    your_fee: int
    expires_at: datetime
    created_at: datetime
    resolved_at: datetime | None


class TradableItemRead(BaseModel):
    item_id: str
    name: str
    value: int


class TradeInfoRead(BaseModel):
    currency: str = "AGC"
    min_level: int
    max_pending_outgoing: int
    max_item_lines: int
    expiry_hours: int
    fee_basis_points: int
    max_value_ratio: int
    player_level: int
    pending_outgoing: int
    tradable: list[TradableItemRead]


class PlayerRead(BaseModel):
    username: str
    level: int
