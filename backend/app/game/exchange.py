"""Regras do mercado entre jogadores (Fase 6).

O preço do anúncio é livre dentro de uma faixa em torno do valor de referência
do entreposto NPC. A faixa existe para controlar a inflação e a transferência de
riqueza entre contas: ninguém consegue "vender por quase nada" a uma conta
parceira nem inflar preços sem limite. A taxa (a mesma do entreposto) é retirada
do vendedor e não volta à economia.
"""

from __future__ import annotations

import math

from app.game.economy import product_prices, seed_prices

# Nível mínimo para anunciar e comprar (protege contas novas e dificulta contas de fachada).
MIN_LEVEL = 3
MAX_ACTIVE_LISTINGS = 20
LISTING_HOURS = 48
MAX_QUANTITY = 999

# Faixa de preço aceita, em % do valor de referência do NPC.
PRICE_FLOOR_PCT = 50
PRICE_CEIL_PCT = 300

STATUS_ACTIVE = "active"
STATUS_SOLD = "sold"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"


def p2p_fee(gross: int, fee_bp: int) -> int:
    """Taxa do vendedor, arredondada **para cima** (mínimo de 1 AGC por compra).

    Diferente do entreposto NPC (que arredonda para baixo), aqui o arredondamento para cima
    impede fatiar uma venda grande em compras minúsculas para não pagar taxa.
    """
    return max(1, -(-gross * fee_bp // 10_000)) if gross > 0 else 0


def reference_prices() -> dict[str, int]:
    """Itens negociáveis e seu valor de referência (sementes e produtos)."""
    return {**seed_prices(), **product_prices()}


def price_bounds(item_id: str) -> tuple[int, int, int] | None:
    """(mínimo, referência, máximo) em AGC por unidade, ou ``None`` se o item não é negociável."""
    reference = reference_prices().get(item_id)
    if reference is None:
        return None
    low = max(1, math.ceil(reference * PRICE_FLOOR_PCT / 100))
    high = max(low, reference * PRICE_CEIL_PCT // 100)
    return low, reference, high
