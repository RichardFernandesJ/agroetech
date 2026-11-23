"""Simulador de paridade entre builds (somente testes).

Estima o lucro por hora de um talhão com a melhor cultura, considerando os
modificadores da build. Serve para impedir que uma especialização domine as
outras: ``test_talent_balance`` exige que todas fiquem na mesma faixa.
"""

from collections.abc import Iterable

from app.game.catalog import CROPS, CropDefinition
from app.game.economy import SALE_FEE_BASIS_POINTS
from app.game.modifiers import BP, Effect, ModifierSet, Stat, effective_fee_bp
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
