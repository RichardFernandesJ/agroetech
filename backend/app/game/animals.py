"""Catálogo de animais e regras puras de alimentação e produção.

Um animal só produz enquanto está alimentado. Cada porção de ração (uma safra
do inventário) o mantém alimentado por ``feed_seconds``; a ração acumulada tem
teto (``max_feed_seconds``), então ninguém "carrega" produção por dias.
Os produtos ficam armazenados no animal (também com teto) até serem coletados.

Tudo aqui é puro (sem banco): dado o instante atual e o estado anterior,
calcula o novo estado. Assim a produção offline é determinística e testável.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.time import ensure_utc

EIGHT_HOURS = 8 * 3600


@dataclass(frozen=True, slots=True)
class AnimalDefinition:
    id: str
    name: str
    description: str
    housing: str  # id da construção que abriga o animal (game/buildings.py)
    price: int  # AGC por animal
    min_player_level: int
    produce_seconds: int  # tempo alimentado para gerar 1 produto
    product_item: str
    product_name: str
    product_description: str
    sell_price: int  # AGC por produto no entreposto
    feed_item: str  # item do inventário usado como ração
    feed_seconds: int  # tempo de alimentação por porção
    xp_per_product: int
    max_feed_seconds: int = EIGHT_HOURS

    @property
    def max_stored(self) -> int:
        """Produtos que o animal guarda: o equivalente à ração máxima acumulada."""
        return math.ceil(self.max_feed_seconds / self.produce_seconds)


ANIMALS: dict[str, AnimalDefinition] = {
    "galinha": AnimalDefinition(
        id="galinha",
        name="Galinha",
        description="Põe ovos o dia todo, desde que bem alimentada com milho.",
        housing="galinheiro",
        price=60,
        min_player_level=2,
        produce_seconds=900,
        product_item="animal_ovo",
        product_name="Ovo",
        product_description="Ovos frescos do galinheiro.",
        sell_price=4,
        feed_item="crop_milho",
        feed_seconds=1800,
        xp_per_product=1,
    ),
    "vaca": AnimalDefinition(
        id="vaca",
        name="Vaca",
        description="Dá leite com constância. Come cenoura.",
        housing="estabulo",
        price=300,
        min_player_level=5,
        produce_seconds=1200,
        product_item="animal_leite",
        product_name="Leite",
        product_description="Leite fresco do estábulo.",
        sell_price=9,
        feed_item="crop_cenoura",
        feed_seconds=1800,
        xp_per_product=2,
    ),
    "ovelha": AnimalDefinition(
        id="ovelha",
        name="Ovelha",
        description="Produz lã de qualidade, mais devagar. Come milho.",
        housing="estabulo",
        price=220,
        min_player_level=7,
        produce_seconds=2400,
        product_item="animal_la",
        product_name="Lã",
        product_description="Lã macia tosquiada no estábulo.",
        sell_price=14,
        feed_item="crop_milho",
        feed_seconds=1800,
        xp_per_product=3,
    ),
}


def get_animal(species_id: str) -> AnimalDefinition | None:
    return ANIMALS.get(species_id)


@dataclass(frozen=True, slots=True)
class Advance:
    progress_seconds: float
    stored: int
    produced: int  # produtos novos guardados
    lost: int  # produtos que não couberam (estoque cheio)


def advance(
    *,
    now: datetime,
    last_sync_at: datetime,
    fed_until: datetime | None,
    progress_seconds: float,
    stored: int,
    produce_seconds: int,
    max_stored: int,
) -> Advance:
    """Acumula a produção entre ``last_sync_at`` e ``now``, só durante o período alimentado."""
    now = ensure_utc(now)
    last_sync_at = ensure_utc(last_sync_at)
    if fed_until is None or now <= last_sync_at:
        return Advance(progress_seconds, stored, 0, 0)

    fed_end = min(now, ensure_utc(fed_until))
    active = max(0.0, (fed_end - last_sync_at).total_seconds())
    if active == 0:
        return Advance(progress_seconds, stored, 0, 0)

    cycles, progress = divmod(progress_seconds + active, produce_seconds)
    cycles = int(cycles)
    gained = min(cycles, max(0, max_stored - stored))
    return Advance(progress, stored + gained, gained, cycles - gained)


@dataclass(frozen=True, slots=True)
class FeedResult:
    fed_until: datetime
    units_used: int


def feed(
    *,
    now: datetime,
    fed_until: datetime | None,
    units: int,
    feed_seconds: int,
    max_feed_seconds: int,
) -> FeedResult:
    """Soma porções de ração até o teto de ``max_feed_seconds`` à frente de ``now``."""
    now = ensure_utc(now)
    current = ensure_utc(fed_until) if fed_until is not None else None
    base = current if current is not None and current > now else now
    room = (now + timedelta(seconds=max_feed_seconds) - base).total_seconds()
    fits = max(0, int(room // feed_seconds))
    used = max(0, min(units, fits))
    return FeedResult(fed_until=base + timedelta(seconds=used * feed_seconds), units_used=used)
