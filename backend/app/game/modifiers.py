"""Motor central de modificadores.

Todo bônus do jogo (talentos hoje; guilda, território e equipamentos depois)
é um :class:`Effect`. As mecânicas nunca somam bônus por conta própria: elas
consultam um :class:`ModifierSet`, que soma as fontes e aplica o teto de cada
estatística. Para criar um talento novo basta declarar efeitos no catálogo.

Valores são inteiros em pontos-base (10.000 = 100%), sem ponto flutuante.
"""

from __future__ import annotations

import random
from collections.abc import Iterable
from dataclasses import dataclass

BP = 10_000


class Stat:
    CROP_YIELD = "crop_yield"
    CROP_GROW_TIME = "crop_grow_time"
    EXTRA_HARVEST_CHANCE = "extra_harvest_chance"
    SEED_SAVE_CHANCE = "seed_save_chance"
    XP_GAIN = "xp_gain"
    SELL_PRICE = "sell_price"
    # Pontos-base subtraídos da taxa de venda (negativo = taxa menor).
    MARKET_FEE = "market_fee"
    # Fabricação: o escopo do tempo é o id da estação (ex.: "moinho").
    PRODUCTION_TIME = "production_time"
    PRODUCTION_YIELD = "production_yield"


# Intervalo permitido para a soma de bônus de cada estatística (em pontos-base).
STAT_LIMITS: dict[str, tuple[int, int]] = {
    Stat.CROP_YIELD: (0, 3_000),
    Stat.CROP_GROW_TIME: (-2_500, 0),
    Stat.EXTRA_HARVEST_CHANCE: (0, 1_000),
    Stat.SEED_SAVE_CHANCE: (0, 3_000),
    Stat.XP_GAIN: (0, 5_000),
    Stat.SELL_PRICE: (0, 4_500),
    Stat.MARKET_FEE: (-400, 0),
    Stat.PRODUCTION_TIME: (-2_500, 0),
    Stat.PRODUCTION_YIELD: (0, 3_000),
}

# Estatísticas cuja mecânica já existe no jogo. Talentos só podem usar estas.
IMPLEMENTED_STATS: frozenset[str] = frozenset(STAT_LIMITS)

# Taxa mínima do entreposto, em pontos-base (1%).
MIN_MARKET_FEE_BP = 100


@dataclass(frozen=True, slots=True)
class Effect:
    stat: str
    value_bp: int
    # ``None`` vale para tudo; um id de cultura restringe o efeito a ela.
    scope: str | None = None


class ModifierSet:
    def __init__(self, effects: Iterable[Effect] = ()) -> None:
        self._effects = tuple(effects)

    @property
    def effects(self) -> tuple[Effect, ...]:
        return self._effects

    def total_bp(self, stat: str, scope: str | None = None) -> int:
        total = sum(
            effect.value_bp
            for effect in self._effects
            if effect.stat == stat and (effect.scope is None or effect.scope == scope)
        )
        low, high = STAT_LIMITS[stat]
        return max(low, min(high, total))

    def snapshot(self, scope: str | None = None) -> dict[str, int]:
        """Totais por estatística (para gravar no plantio ou exibir na interface)."""
        return {stat: self.total_bp(stat, scope) for stat in STAT_LIMITS}


def seeded_rng(*parts: object) -> random.Random:
    """Gerador determinístico: o mesmo evento sempre produz o mesmo sorteio."""
    return random.Random(":".join(str(part) for part in parts))


def scale(base: int, bonus_bp: int, rng: random.Random) -> int:
    """``base * (1 + bônus)`` com arredondamento estocástico determinístico.

    A parte fracionária vira uma chance de +1, então bônus pequenos sobre
    quantidades pequenas não são perdidos, e a média bate com o valor exato.
    """
    quotient, remainder = divmod(base * (BP + bonus_bp), BP)
    if remainder and rng.randrange(BP) < remainder:
        quotient += 1
    return quotient


def roll(chance_bp: int, rng: random.Random) -> bool:
    return chance_bp > 0 and rng.randrange(BP) < chance_bp


def scaled_seconds(base_seconds: int, bonus_bp: int) -> int:
    return max(1, base_seconds * (BP + bonus_bp) // BP)


def effective_fee_bp(base_fee_bp: int, bonus_bp: int) -> int:
    return max(MIN_MARKET_FEE_BP, base_fee_bp + bonus_bp)
