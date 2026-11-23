"""Parâmetros da economia do AgroCoin (AGC).

Todos os valores são inteiros (AGC não tem centavos) e definidos no servidor:
o frontend nunca envia preço. Preços de compra/venda ficam no catálogo
(``CropDefinition.seed_price`` / ``sell_price``).
"""

from __future__ import annotations

from app.game.catalog import CROPS

# Crédito único dado na criação da carteira. Única emissão sem contrapartida.
INITIAL_GRANT_AGC = 100

# Taxa do entreposto sobre vendas, em pontos-base (500 = 5%). É um sumidouro:
# o valor retido não volta ao jogador.
SALE_FEE_BASIS_POINTS = 500

MAX_TRADE_QUANTITY = 999


def seed_prices() -> dict[str, int]:
    return {crop.seed_item: crop.seed_price for crop in CROPS.values()}


def product_prices() -> dict[str, int]:
    return {crop.product_item: crop.sell_price for crop in CROPS.values()}


def sale_fee(gross: int, fee_bp: int = SALE_FEE_BASIS_POINTS) -> int:
    """Taxa em AGC, arredondada para baixo (nunca cobra mais que o devido)."""
    return gross * fee_bp // 10_000
