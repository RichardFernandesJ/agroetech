"""Schemas do mercado (entreposto NPC)."""

from pydantic import BaseModel, Field

from app.game.economy import MAX_TRADE_QUANTITY


class TradeRequest(BaseModel):
    item_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=MAX_TRADE_QUANTITY)


class OfferRead(BaseModel):
    item_id: str
    name: str
    category: str
    # Preço pago pelo jogador ao comprar (None = o entreposto não vende).
    buy_price: int | None
    # Preço recebido pelo jogador ao vender, antes da taxa (None = não compra).
    sell_price: int | None


class MarketOffersRead(BaseModel):
    currency: str = "AGC"
    fee_basis_points: int
    offers: list[OfferRead]


class TradeRead(BaseModel):
    kind: str
    item_id: str
    item_name: str
    quantity: int
    unit_price: int
    gross: int
    fee: int
    # Variação efetiva do saldo (negativa na compra, positiva na venda).
    amount: int
    balance: int
    # True quando a chave de idempotência já havia sido processada.
    replayed: bool
