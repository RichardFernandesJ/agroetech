"""Schemas do mercado entre jogadores."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.game.exchange import MAX_QUANTITY


class PriceRead(BaseModel):
    item_id: str
    name: str
    reference: int
    minimum: int
    maximum: int
    # Média das últimas negociações e o menor anúncio ativo (None se ainda não houver).
    last_price: int | None
    lowest_listing: int | None


class ExchangeInfoRead(BaseModel):
    currency: str = "AGC"
    min_level: int
    max_active_listings: int
    listing_hours: int
    # Taxa que o vendedor paga em cada venda, em pontos-base (500 = 5%).
    fee_basis_points: int
    player_level: int
    active_listings: int
    prices: list[PriceRead]


class ListingRead(BaseModel):
    id: uuid.UUID
    seller_name: str
    is_mine: bool
    item_id: str
    item_name: str
    quantity_initial: int
    quantity_remaining: int
    unit_price: int
    status: str
    expires_at: datetime
    created_at: datetime


class CreateListingRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=MAX_QUANTITY)
    unit_price: int = Field(ge=1, le=1_000_000)


class BuyListingRequest(BaseModel):
    quantity: int = Field(ge=1, le=MAX_QUANTITY)


class TradeRead(BaseModel):
    transaction_id: uuid.UUID
    listing_id: uuid.UUID
    item_id: str
    item_name: str
    quantity: int
    unit_price: int
    gross: int
    fee: int
    seller_net: int
    # Saldo do comprador depois da compra.
    balance: int
    listing_remaining: int
    listing_status: str
    replayed: bool


class HistoryRead(BaseModel):
    id: uuid.UUID
    role: str  # "buyer" | "seller"
    counterpart: str
    item_id: str
    item_name: str
    quantity: int
    unit_price: int
    gross: int
    fee: int
    # Variação do saldo do jogador: -bruto (compra) ou +líquido (venda).
    amount: int
    created_at: datetime
