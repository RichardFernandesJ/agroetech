"""Curva de experiência e níveis do jogador.

Funções puras (sem banco): o nível é sempre derivado do XP acumulado, nunca
armazenado, para que XP e nível jamais divirjam.

XP total para alcançar o nível ``L``: ``25 * (L - 1) * L``
(nível 2 = 50, nível 10 = 2.250, nível 50 = 61.250).
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_LEVEL = 50

# XP ganho ao plantar uma semente (a colheita rende XP por ciclo, definido no catálogo).
PLANT_XP = 2


def total_xp_for_level(level: int) -> int:
    level = max(1, min(level, MAX_LEVEL))
    return 25 * (level - 1) * level


MAX_XP = total_xp_for_level(MAX_LEVEL)


def level_for_xp(xp: int) -> int:
    xp = max(0, min(xp, MAX_XP))
    level = 1
    while level < MAX_LEVEL and xp >= total_xp_for_level(level + 1):
        level += 1
    return level


@dataclass(frozen=True, slots=True)
class LevelInfo:
    level: int
    xp: int
    xp_into_level: int
    # XP necessário neste nível para alcançar o próximo (None no nível máximo).
    xp_for_next: int | None
    max_level: int


def describe(xp: int) -> LevelInfo:
    xp = max(0, min(xp, MAX_XP))
    level = level_for_xp(xp)
    floor = total_xp_for_level(level)
    next_total = total_xp_for_level(level + 1) if level < MAX_LEVEL else None
    return LevelInfo(
        level=level,
        xp=xp,
        xp_into_level=xp - floor,
        xp_for_next=None if next_total is None else next_total - floor,
        max_level=MAX_LEVEL,
    )
