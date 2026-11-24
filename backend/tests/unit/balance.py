"""Simulador de paridade entre builds (somente testes).

Estima o lucro por hora de um talhão com a melhor cultura, considerando os
modificadores da build. Serve para impedir que uma especialização domine as
outras: ``test_talent_balance`` exige que todas fiquem na mesma faixa.
"""

from collections.abc import Iterable

from app.game.animals import ANIMALS, AnimalDefinition
from app.game.catalog import CROPS, CropDefinition, sell_scope_for_item
from app.game.economy import SALE_FEE_BASIS_POINTS, product_prices
from app.game.modifiers import BP, Effect, ModifierSet, Stat, effective_fee_bp
from app.game.recipes import RECIPES, RecipeDefinition
from app.game.talents import NODES_BY_ID


def modifiers_for_nodes(node_ids: Iterable[str]) -> ModifierSet:
    effects: list[Effect] = []
    for node_id in node_ids:
        effects.extend(NODES_BY_ID[node_id].effects)
    return ModifierSet(effects)


def profit_per_hour(crop: CropDefinition, mods: ModifierSet) -> float:
    """AGC por hora de um talhão dedicado a ``crop`` (valores esperados)."""
    cycle_seconds = crop.grow_seconds * (BP + mods.total_bp(Stat.CROP_GROW_TIME, crop.id)) / BP
    units = crop.yield_quantity * (BP + mods.total_bp(Stat.CROP_YIELD, crop.id)) / BP
    units += crop.yield_quantity * mods.total_bp(Stat.EXTRA_HARVEST_CHANCE, crop.id) / BP
    price = crop.sell_price * (BP + mods.total_bp(Stat.SELL_PRICE, crop.id)) / BP
    fee_bp = effective_fee_bp(SALE_FEE_BASIS_POINTS, mods.total_bp(Stat.MARKET_FEE))
    revenue = units * price * (BP - fee_bp) / BP
    # Toda colheita devolve ao menos 1 semente (seed_yield), então o talhão se replanta
    # sem custo: o lucro por hora é a receita líquida.
    cost = 0.0
    return (revenue - cost) * 3600 / cycle_seconds


def best_profit_per_hour(node_ids: Iterable[str]) -> float:
    mods = modifiers_for_nodes(node_ids)
    return max(profit_per_hour(crop, mods) for crop in CROPS.values())


def xp_per_hour(node_ids: Iterable[str]) -> float:
    mods = modifiers_for_nodes(node_ids)
    best = 0.0
    for crop in CROPS.values():
        cycle = crop.grow_seconds * (BP + mods.total_bp(Stat.CROP_GROW_TIME, crop.id)) / BP
        xp = crop.harvest_xp * (BP + mods.total_bp(Stat.XP_GAIN, crop.id)) / BP
        best = max(best, xp * 3600 / cycle)
    return best


def _net_price(item_id: str, mods: ModifierSet) -> float:
    """O que o jogador recebe por 1 unidade vendida (bônus de preço e taxa efetiva)."""
    bonus = mods.total_bp(Stat.SELL_PRICE, sell_scope_for_item(item_id))
    fee_bp = effective_fee_bp(SALE_FEE_BASIS_POINTS, mods.total_bp(Stat.MARKET_FEE))
    return product_prices()[item_id] * (BP + bonus) / BP * (BP - fee_bp) / BP


def animal_profit_per_hour(animal: AnimalDefinition, mods: ModifierSet) -> float:
    """AGC por hora de um animal: produtos vendidos menos o valor da ração consumida."""
    speed = mods.total_bp(Stat.ANIMAL_SPEED, animal.id)
    yield_bp = mods.total_bp(Stat.ANIMAL_YIELD, animal.id)
    efficiency = mods.total_bp(Stat.FEED_EFFICIENCY, animal.id)
    produce_seconds = animal.produce_seconds * (BP + speed) / BP
    revenue = 3600 / produce_seconds * (BP + yield_bp) / BP * _net_price(animal.product_item, mods)
    feed_seconds = animal.feed_seconds * (BP + efficiency) / BP
    feed_cost = 3600 / feed_seconds * product_prices()[animal.feed_item]
    return revenue - feed_cost


def best_animal_profit_per_hour(node_ids: Iterable[str]) -> float:
    mods = modifiers_for_nodes(node_ids)
    return max(animal_profit_per_hour(animal, mods) for animal in ANIMALS.values())


def craft_profit_per_hour(recipe: RecipeDefinition, mods: ModifierSet) -> float:
    """AGC por hora de uma vaga da estação (receita vendida menos os insumos gastos)."""
    station = recipe.station
    seconds = recipe.duration_seconds * (BP + mods.total_bp(Stat.PRODUCTION_TIME, station)) / BP
    output = recipe.output_quantity * (BP + mods.total_bp(Stat.PRODUCTION_YIELD, station)) / BP
    saving = mods.total_bp(Stat.PRODUCTION_SAVING, station) / BP
    prices = product_prices()
    inputs = sum(prices[item] * quantity for item, quantity in recipe.inputs.items()) * (1 - saving)
    return (output * _net_price(recipe.output_item, mods) - inputs) * 3600 / seconds


def best_craft_profit_per_hour(node_ids: Iterable[str]) -> float:
    mods = modifiers_for_nodes(node_ids)
    return max(craft_profit_per_hour(recipe, mods) for recipe in RECIPES.values())


# Builds de referência no nível 50 (49 pontos), todas válidas pelas regras reais.
BUILDS: dict[str, list[str]] = {
    "agricultor": [
        "agro_solo_fertil",
        "agro_sementes_vigorosas",
        "agro_olho_clinico",
        "agro_especialista_milho",
        "agro_horticultor",
        "agro_cafeicultor",
        "agro_economia_sementes",
        "agro_irrigacao",
        "agro_colheita_farta",
        "agro_rotacao",
        "agro_mestre_terra",
        "agro_colheita_dourada",
        "com_regateio",
        "com_balanca_justa",
        "com_contatos",
        "com_taxa_reduzida",
        "com_hortalicas",
        "com_graos",
        "hib_contratos_safra",
        "com_negociador",
    ],
    "comerciante": [
        "com_regateio",
        "com_balanca_justa",
        "com_contatos",
        "com_graos",
        "com_hortalicas",
        "com_frutas_finas",
        "com_taxa_reduzida",
        "com_negociador",
        "com_corretor",
        "com_rede_clientes",
        "com_mestre_mercado",
        "com_barao",
        "agro_solo_fertil",
        "agro_sementes_vigorosas",
        "agro_olho_clinico",
        "agro_especialista_milho",
        "agro_horticultor",
        "agro_economia_sementes",
        "hib_contratos_safra",
        "agro_irrigacao",
    ],
    "hibrido": [
        "agro_solo_fertil",
        "agro_sementes_vigorosas",
        "agro_olho_clinico",
        "agro_especialista_milho",
        "agro_horticultor",
        "agro_cafeicultor",
        "agro_economia_sementes",
        "agro_irrigacao",
        "agro_colheita_farta",
        "agro_rotacao",
        "com_regateio",
        "com_balanca_justa",
        "com_contatos",
        "com_graos",
        "com_hortalicas",
        "com_frutas_finas",
        "com_taxa_reduzida",
        "com_negociador",
        "com_corretor",
        "com_rede_clientes",
        "hib_contratos_safra",
        "agro_mestre_terra",
    ],
}

_PEC_CORE = [
    "pec_pasto_verde",
    "pec_cocho_farto",
    "pec_manejo",
    "pec_avicultor",
    "pec_leiteiro",
    "pec_pastor",
    "pec_silagem",
    "pec_genetica",
    "pec_ordenha",
    "pec_nutricao",
    "pec_mestre_rebanho",
    "pec_fazenda_modelo",
]
_IND_CORE = [
    "ind_ferramentas",
    "ind_aproveitamento",
    "ind_boa_receita",
    "ind_moleiro",
    "ind_padeiro",
    "ind_queijeiro",
    "ind_estoque",
    "ind_linha",
    "ind_otimizacao",
    "ind_qualidade",
    "ind_mestre_eficiencia",
    "ind_fabrica",
]

# Builds de produção animal e de fabricação no nível 50 (49 pontos).
DOMAIN_BUILDS: dict[str, list[str]] = {
    "pecuarista": [
        *_PEC_CORE,
        "com_regateio",
        "com_balanca_justa",
        "com_contatos",
        "com_graos",
        "com_hortalicas",
        "hib_feira_pecuaria",
    ],
    "industrial": [
        *_IND_CORE,
        "pec_pasto_verde",
        "pec_cocho_farto",
        "pec_manejo",
        "pec_avicultor",
        "pec_leiteiro",
        "hib_laticinios",
    ],
}
