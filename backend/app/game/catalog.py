"""Catálogo estático de culturas e itens.

O catálogo fica em código (e não no banco) porque é conteúdo do jogo, versionado
junto com o balanceamento. Se no futuro ele precisar ser editável pelo painel,
pode migrar para uma tabela sem mudar os services: basta trocar as funções de
consulta deste módulo.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CropDefinition:
    id: str
    name: str
    description: str
    grow_seconds: int
    yield_quantity: int
    seed_yield: int
    max_cycles: int
    seed_price: int  # AGC cobrados pelo entreposto ao comprar 1 semente
    sell_price: int  # AGC pagos pelo entreposto por 1 unidade da safra

    @property
    def seed_item(self) -> str:
        return f"seed_{self.id}"

    @property
    def product_item(self) -> str:
        return f"crop_{self.id}"


@dataclass(frozen=True, slots=True)
class ItemDefinition:
    id: str
    name: str
    category: str  # "seed" | "product"
    description: str


CROPS: dict[str, CropDefinition] = {
    "milho": CropDefinition(
        id="milho",
        name="Milho",
        description="Cultura de ciclo curto e colheita única. Ótima para começar.",
        grow_seconds=300,
        yield_quantity=3,
        seed_yield=1,
        max_cycles=1,
        seed_price=8,
        sell_price=5,
    ),
    "cenoura": CropDefinition(
        id="cenoura",
        name="Cenoura",
        description="Cresce rápido e rende boas moedas no inventário.",
        grow_seconds=600,
        yield_quantity=4,
        seed_yield=1,
        max_cycles=1,
        seed_price=14,
        sell_price=6,
    ),
    "tomate": CropDefinition(
        id="tomate",
        name="Tomate",
        description="Produz várias colheitas antes de esgotar o pé.",
        grow_seconds=900,
        yield_quantity=3,
        seed_yield=1,
        max_cycles=3,
        seed_price=22,
        sell_price=6,
    ),
    "morango": CropDefinition(
        id="morango",
        name="Morango",
        description="Colheita demorada, porém generosa e recorrente.",
        grow_seconds=1200,
        yield_quantity=5,
        seed_yield=1,
        max_cycles=4,
        seed_price=30,
        sell_price=6,
    ),
    "cafe": CropDefinition(
        id="cafe",
        name="Café",
        description="Lavoura de alto valor, com longo ciclo e muitas safras.",
        grow_seconds=3600,
        yield_quantity=8,
        seed_yield=1,
        max_cycles=6,
        seed_price=90,
        sell_price=9,
    ),
}


def get_crop(crop_id: str) -> CropDefinition | None:
    return CROPS.get(crop_id)


# Sementes iniciais entregues ao criar uma propriedade.
STARTER_SEEDS: dict[str, int] = {
    "seed_milho": 6,
    "seed_cenoura": 4,
    "seed_tomate": 3,
    "seed_morango": 2,
    "seed_cafe": 1,
}


def _build_item_catalog() -> dict[str, ItemDefinition]:
    catalog: dict[str, ItemDefinition] = {}
    for crop in CROPS.values():
        catalog[crop.seed_item] = ItemDefinition(
            id=crop.seed_item,
            name=f"Semente de {crop.name.lower()}",
            category="seed",
            description=f"Semente usada para plantar {crop.name.lower()}.",
        )
        catalog[crop.product_item] = ItemDefinition(
            id=crop.product_item,
            name=crop.name,
            category="product",
            description=crop.description,
        )
    return catalog


ITEM_CATALOG: dict[str, ItemDefinition] = _build_item_catalog()


def get_item(item_id: str) -> ItemDefinition | None:
    return ITEM_CATALOG.get(item_id)
