"""Regras das trocas diretas entre dois jogadores (Fase 6).

Uma proposta oferece itens e/ou AGC em troca de itens e/ou AGC do outro jogador. O lado do
proponente fica em custódia até o destinatário aceitar, recusar, ou a proposta ser cancelada ou
expirar. Para a troca não virar um canal de "presentes" entre contas de fachada (que
contornaria a faixa de preço da Praça), os dois lados precisam ter valor e a diferença entre
eles é limitada pelos valores de referência do entreposto.
"""

from __future__ import annotations

from app.game.exchange import MIN_LEVEL, reference_prices

TRADE_MIN_LEVEL = MIN_LEVEL
MAX_PENDING_OUTGOING = 5
MAX_ITEM_LINES = 4
MAX_ITEM_QUANTITY = 999
MAX_AGC = 1_000_000
EXPIRY_HOURS = 24
# O lado de maior valor pode valer, no máximo, 3x o de menor valor.
MAX_VALUE_RATIO = 3
# Taxa de cada parte sobre o valor do que ela entrega (2%, arredondada para cima).
TRADE_FEE_BP = 200

STATUS_PENDING = "pending"
STATUS_ACCEPTED = "accepted"
STATUS_DECLINED = "declined"
STATUS_CANCELLED = "cancelled"
STATUS_EXPIRED = "expired"

SIDE_OFFER = "offer"
SIDE_REQUEST = "request"


def side_value(items: list[tuple[str, int]], agc: int) -> int:
    """Valor de referência de um lado (itens pelo preço do entreposto + AGC 1:1)."""
    prices = reference_prices()
    return sum(prices[item_id] * quantity for item_id, quantity in items) + agc


def trade_fee(value: int) -> int:
    """Taxa de uma parte, arredondada para cima (mínimo de 1 AGC quando há valor)."""
    return max(1, -(-value * TRADE_FEE_BP // 10_000)) if value > 0 else 0


def ratio_ok(offer_value: int, request_value: int) -> bool:
    low, high = sorted((offer_value, request_value))
    return low > 0 and high <= low * MAX_VALUE_RATIO
