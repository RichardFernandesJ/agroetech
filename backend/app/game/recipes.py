"""Catálogo de receitas de fabricação (conteúdo do jogo, versionado em código).

Cada receita roda em uma estação (uma construção de ``game/buildings.py``),
consome itens do inventário e, depois de ``duration_seconds`` por lote, entrega
um produto processado de maior valor. Os insumos vêm da lavoura e dos animais,
fechando a cadeia: plantar → criar → processar → vender.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RecipeDefinition:
    id: str
    name: str
    station: str  # id da construção (game/buildings.py)
    inputs: dict[str, int]  # item_id -> quantidade por lote
    output_item: str
    output_quantity: int  # por lote
    duration_seconds: int  # por lote
    min_player_level: int
    xp: int  # por lote coletado
    description: str = ""
    # Itens processados novos precisam de nome/descrição/preço (ver PROCESSED_ITEMS).
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ProcessedItem:
    id: str
    name: str
    description: str
    sell_price: int  # AGC no entreposto


PROCESSED_ITEMS: dict[str, ProcessedItem] = {
    "processed_farinha": ProcessedItem(
        "processed_farinha", "Farinha de milho", "Farinha moída na hora no moinho.", 30
    ),
    "processed_pao": ProcessedItem("processed_pao", "Pão", "Pão quentinho de forno a lenha.", 40),
    "processed_bolo": ProcessedItem(
        "processed_bolo", "Bolo", "Bolo caseiro com ovos, leite e farinha.", 150
    ),
    "processed_queijo": ProcessedItem(
        "processed_queijo", "Queijo", "Queijo curado da queijaria da ilha.", 52
    ),
    "processed_manteiga": ProcessedItem(
        "processed_manteiga", "Manteiga", "Manteiga fresca batida à mão.", 34
    ),
}

RECIPES: dict[str, RecipeDefinition] = {
    "farinha": RecipeDefinition(
        id="farinha",
        name="Farinha de milho",
        station="moinho",
        inputs={"crop_milho": 3},
        output_item="processed_farinha",
        output_quantity=1,
        duration_seconds=600,
        min_player_level=3,
        xp=4,
        description="Mói o milho da lavoura em farinha.",
    ),
    "pao": RecipeDefinition(
        id="pao",
        name="Pão",
        station="padaria",
        inputs={"processed_farinha": 2, "animal_ovo": 1},
        output_item="processed_pao",
        output_quantity=3,
        duration_seconds=900,
        min_player_level=5,
        xp=6,
        description="Assa pães com farinha e ovos.",
    ),
    "bolo": RecipeDefinition(
        id="bolo",
        name="Bolo",
        station="padaria",
        inputs={"processed_farinha": 2, "animal_ovo": 2, "animal_leite": 1},
        output_item="processed_bolo",
        output_quantity=1,
        duration_seconds=1800,
        min_player_level=9,
        xp=12,
        description="Um bolo de festa: farinha, ovos e leite.",
    ),
    "queijo": RecipeDefinition(
        id="queijo",
        name="Queijo",
        station="queijaria",
        inputs={"animal_leite": 3},
        output_item="processed_queijo",
        output_quantity=1,
        duration_seconds=1200,
        min_player_level=6,
        xp=8,
        description="Coalha e cura o leite em queijo.",
    ),
    "manteiga": RecipeDefinition(
        id="manteiga",
        name="Manteiga",
        station="queijaria",
        inputs={"animal_leite": 2},
        output_item="processed_manteiga",
        output_quantity=1,
        duration_seconds=600,
        min_player_level=6,
        xp=4,
        description="Bate o leite até virar manteiga.",
    ),
}

MAX_BATCHES = 24


def get_recipe(recipe_id: str) -> RecipeDefinition | None:
    return RECIPES.get(recipe_id)
