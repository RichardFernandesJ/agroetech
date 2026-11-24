"""Catálogo de talentos (conteúdo do jogo, versionado em código).

O mapa tem seis setores (ramos). Apenas os ramos cuja mecânica já existe têm
talentos com efeito; os demais aparecem bloqueados ("em breve") na interface.
Veja ``docs/TALENTS.md`` para o desenho completo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.game.animals import ANIMALS
from app.game.catalog import CROPS
from app.game.modifiers import IMPLEMENTED_STATS, Effect, Stat
from app.game.recipes import PROCESSED_ITEMS, RECIPES

# camada -> (custo em pontos, nível mínimo)
TIERS: dict[int, tuple[int, int]] = {
    1: (1, 2),  # básico
    2: (2, 5),  # intermediário
    3: (3, 10),  # avançado
    4: (5, 20),  # mestre
    5: (8, 35),  # lendário
}

# Pontos já investidos no próprio ramo exigidos por camada (força especialização).
BRANCH_GATES: dict[int, int] = {1: 0, 2: 2, 3: 8, 4: 16, 5: 24}

TIER_NAMES = {1: "Básico", 2: "Intermediário", 3: "Avançado", 4: "Mestre", 5: "Lendário"}

MAP_CENTER = (1000, 1000)


@dataclass(frozen=True, slots=True)
class Branch:
    id: str
    name: str
    description: str
    available: bool
    angle: int  # graus, centro do setor no mapa


BRANCHES: tuple[Branch, ...] = (
    Branch(
        "agricultura",
        "Agricultura e Produção",
        "Produtividade, tempo e técnicas de cultivo.",
        True,
        270,
    ),
    Branch("comercio", "Comércio e Economia", "Preços, taxas e negociações.", True, 330),
    Branch("pecuaria", "Pecuária e Criação", "Animais e seus produtos.", True, 30),
    Branch("industria", "Indústria e Tecnologia", "Processamento e automação.", True, 90),
    Branch(
        "exploracao",
        "Exploração e Conhecimento",
        "Recursos raros, regiões e expedições.",
        False,
        150,
    ),
    Branch("estrategia", "Estratégia, Defesa e Combate", "Defesa, guildas e disputas.", False, 210),
)

HYBRID = "hibrido"


@dataclass(frozen=True, slots=True)
class TalentNode:
    id: str
    name: str
    description: str
    branch: str
    tier: int
    effects: tuple[Effect, ...]
    x: int
    y: int
    requires: tuple[str, ...] = ()  # todos exigidos
    requires_any: tuple[str, ...] = ()  # pelo menos um
    branch_points: tuple[tuple[str, int], ...] = ()  # pontos exigidos em ramos
    exclusive_group: str | None = None

    @property
    def cost(self) -> int:
        return TIERS[self.tier][0]

    @property
    def min_level(self) -> int:
        return TIERS[self.tier][1]


_BRANCH_BY_ID = {branch.id: branch for branch in BRANCHES}


def _position(angle_deg: float, tier: int) -> tuple[int, int]:
    radius = 140 + tier * 130
    radians = math.radians(angle_deg)
    return (
        MAP_CENTER[0] + round(radius * math.cos(radians)),
        MAP_CENTER[1] + round(radius * math.sin(radians)),
    )


def _node(
    node_id: str,
    name: str,
    description: str,
    branch: str,
    tier: int,
    lane: float,
    effects: tuple[Effect, ...],
    *,
    requires: tuple[str, ...] = (),
    requires_any: tuple[str, ...] = (),
    exclusive_group: str | None = None,
    branch_points: tuple[tuple[str, int], ...] | None = None,
    angle: float | None = None,
) -> TalentNode:
    if angle is None:
        angle = _BRANCH_BY_ID[branch].angle + lane * 14
    if branch_points is None:
        gate = BRANCH_GATES[tier]
        branch_points = ((branch, gate),) if gate and branch in _BRANCH_BY_ID else ()
    x, y = _position(angle, tier)
    return TalentNode(
        id=node_id,
        name=name,
        description=description,
        branch=branch,
        tier=tier,
        effects=effects,
        x=x,
        y=y,
        requires=requires,
        requires_any=requires_any,
        branch_points=branch_points,
        exclusive_group=exclusive_group,
    )


def _e(stat: str, pct: float, scope: str | None = None) -> Effect:
    """Efeito em porcentagem (ex.: 3 = +3%; para taxa, em pontos percentuais)."""
    return Effect(stat, round(pct * 100), scope)


_AGRO = "agricultura"
_COM = "comercio"
_PEC = "pecuaria"
_IND = "industria"

NODES: tuple[TalentNode, ...] = (
    # ----------------------------------------------------------------- Agricultura
    _node(
        "agro_solo_fertil",
        "Solo Fértil",
        "+2% de produção em todas as colheitas.",
        _AGRO,
        1,
        -1,
        (_e(Stat.CROP_YIELD, 2),),
    ),
    _node(
        "agro_sementes_vigorosas",
        "Sementes Vigorosas",
        "-2% no tempo de crescimento.",
        _AGRO,
        1,
        0,
        (_e(Stat.CROP_GROW_TIME, -2),),
    ),
    _node(
        "agro_olho_clinico",
        "Olho Clínico",
        "+3% de XP em plantio e colheita.",
        _AGRO,
        1,
        1,
        (_e(Stat.XP_GAIN, 3),),
    ),
    _node(
        "agro_especialista_milho",
        "Especialista em Milho",
        "Milho: +6% de produção, +10% de XP e -3% no tempo de crescimento.",
        _AGRO,
        2,
        -1.5,
        (
            _e(Stat.CROP_YIELD, 6, "milho"),
            _e(Stat.XP_GAIN, 10, "milho"),
            _e(Stat.CROP_GROW_TIME, -3, "milho"),
        ),
        requires=("agro_solo_fertil",),
    ),
    _node(
        "agro_horticultor",
        "Horticultor",
        "Cenoura e tomate: +6% de produção e +8% de XP.",
        _AGRO,
        2,
        -0.5,
        (
            _e(Stat.CROP_YIELD, 6, "cenoura"),
            _e(Stat.CROP_YIELD, 6, "tomate"),
            _e(Stat.XP_GAIN, 8, "cenoura"),
            _e(Stat.XP_GAIN, 8, "tomate"),
        ),
        requires_any=("agro_solo_fertil", "agro_olho_clinico"),
    ),
    _node(
        "agro_cafeicultor",
        "Cafeicultor",
        "Café e morango: +6% de produção e +8% de XP.",
        _AGRO,
        2,
        0.5,
        (
            _e(Stat.CROP_YIELD, 6, "cafe"),
            _e(Stat.CROP_YIELD, 6, "morango"),
            _e(Stat.XP_GAIN, 8, "cafe"),
            _e(Stat.XP_GAIN, 8, "morango"),
        ),
        requires=("agro_olho_clinico",),
    ),
    _node(
        "agro_economia_sementes",
        "Economia de Sementes",
        "5% de chance de não gastar a semente ao plantar.",
        _AGRO,
        2,
        1.5,
        (_e(Stat.SEED_SAVE_CHANCE, 5),),
        requires=("agro_sementes_vigorosas",),
    ),
    _node(
        "agro_irrigacao",
        "Irrigação Eficiente",
        "-5% no tempo de crescimento.",
        _AGRO,
        3,
        -1,
        (_e(Stat.CROP_GROW_TIME, -5),),
        requires_any=("agro_especialista_milho", "agro_horticultor", "agro_economia_sementes"),
    ),
    _node(
        "agro_colheita_farta",
        "Colheita Farta",
        "4% de chance de colher um ciclo extra de produção.",
        _AGRO,
        3,
        0,
        (_e(Stat.EXTRA_HARVEST_CHANCE, 4),),
        requires_any=("agro_horticultor", "agro_cafeicultor"),
    ),
    _node(
        "agro_rotacao",
        "Rotação de Culturas",
        "+4% de produção e +6% de XP.",
        _AGRO,
        3,
        1,
        (_e(Stat.CROP_YIELD, 4), _e(Stat.XP_GAIN, 6)),
        requires_any=("agro_cafeicultor", "agro_economia_sementes"),
    ),
    _node(
        "agro_mestre_terra",
        "Mestre da Terra",
        "+8% de produção e +3% de chance de colheita extra.",
        _AGRO,
        4,
        -0.5,
        (_e(Stat.CROP_YIELD, 8), _e(Stat.EXTRA_HARVEST_CHANCE, 3)),
        requires_any=("agro_colheita_farta", "agro_rotacao"),
        exclusive_group="agro_mestre",
    ),
    _node(
        "agro_mestre_tempo",
        "Mestre do Tempo",
        "-10% no tempo de crescimento e +10% de chance de poupar sementes.",
        _AGRO,
        4,
        0.5,
        (_e(Stat.CROP_GROW_TIME, -10), _e(Stat.SEED_SAVE_CHANCE, 10)),
        requires_any=("agro_irrigacao", "agro_rotacao"),
        exclusive_group="agro_mestre",
    ),
    _node(
        "agro_colheita_dourada",
        "Colheita Dourada",
        "+10% de produção, +3% de colheita extra e +10% de XP.",
        _AGRO,
        5,
        0,
        (_e(Stat.CROP_YIELD, 10), _e(Stat.EXTRA_HARVEST_CHANCE, 3), _e(Stat.XP_GAIN, 10)),
        requires_any=("agro_mestre_terra", "agro_mestre_tempo"),
    ),
    # -------------------------------------------------------------------- Comércio
    _node(
        "com_regateio",
        "Regateio",
        "+3% no preço de venda de tudo.",
        _COM,
        1,
        -1,
        (_e(Stat.SELL_PRICE, 3),),
    ),
    _node(
        "com_balanca_justa",
        "Balança Justa",
        "Taxa de venda 0,5 ponto menor.",
        _COM,
        1,
        0,
        (_e(Stat.MARKET_FEE, -0.5),),
    ),
    _node(
        "com_contatos",
        "Contatos",
        "+2% de XP e +1% no preço de venda.",
        _COM,
        1,
        1,
        (_e(Stat.XP_GAIN, 2), _e(Stat.SELL_PRICE, 1)),
    ),
    _node(
        "com_graos",
        "Mercador de Grãos",
        "Milho: +10% no preço de venda.",
        _COM,
        2,
        -1.5,
        (_e(Stat.SELL_PRICE, 10, "milho"),),
        requires=("com_regateio",),
    ),
    _node(
        "com_hortalicas",
        "Feirante",
        "Cenoura e tomate: +10% no preço de venda.",
        _COM,
        2,
        -0.5,
        (_e(Stat.SELL_PRICE, 10, "cenoura"), _e(Stat.SELL_PRICE, 10, "tomate")),
        requires_any=("com_regateio", "com_contatos"),
    ),
    _node(
        "com_frutas_finas",
        "Barão do Café e das Frutas",
        "Café e morango: +10% no preço de venda.",
        _COM,
        2,
        0.5,
        (_e(Stat.SELL_PRICE, 10, "cafe"), _e(Stat.SELL_PRICE, 10, "morango")),
        requires=("com_contatos",),
    ),
    _node(
        "com_taxa_reduzida",
        "Taxa Reduzida",
        "Taxa de venda 1 ponto menor.",
        _COM,
        2,
        1.5,
        (_e(Stat.MARKET_FEE, -1),),
        requires=("com_balanca_justa",),
    ),
    _node(
        "com_negociador",
        "Negociador",
        "+6% no preço de venda de tudo.",
        _COM,
        3,
        -1,
        (_e(Stat.SELL_PRICE, 6),),
        requires_any=("com_graos", "com_hortalicas"),
    ),
    _node(
        "com_corretor",
        "Corretor",
        "Taxa de venda 1 ponto menor.",
        _COM,
        3,
        0,
        (_e(Stat.MARKET_FEE, -1),),
        requires_any=("com_taxa_reduzida", "com_hortalicas"),
    ),
    _node(
        "com_rede_clientes",
        "Rede de Clientes",
        "+4% no preço de venda e +6% de XP.",
        _COM,
        3,
        1,
        (_e(Stat.SELL_PRICE, 4), _e(Stat.XP_GAIN, 6)),
        requires_any=("com_frutas_finas", "com_taxa_reduzida"),
    ),
    _node(
        "com_mestre_mercado",
        "Mestre do Mercado",
        "+10% no preço de venda e taxa 0,5 ponto menor.",
        _COM,
        4,
        -0.5,
        (_e(Stat.SELL_PRICE, 10), _e(Stat.MARKET_FEE, -0.5)),
        requires_any=("com_negociador", "com_corretor"),
        exclusive_group="com_mestre",
    ),
    _node(
        "com_mestre_contratos",
        "Mestre dos Contratos",
        "Taxa de venda 1,5 ponto menor e +5% de XP.",
        _COM,
        4,
        0.5,
        (_e(Stat.MARKET_FEE, -1.5), _e(Stat.XP_GAIN, 5)),
        requires_any=("com_corretor", "com_rede_clientes"),
        exclusive_group="com_mestre",
    ),
    _node(
        "com_barao",
        "Barão do Comércio",
        "+12% no preço de venda e taxa 1 ponto menor.",
        _COM,
        5,
        0,
        (_e(Stat.SELL_PRICE, 12), _e(Stat.MARKET_FEE, -1)),
        requires_any=("com_mestre_mercado", "com_mestre_contratos"),
    ),
    # --------------------------------------------------------------------- Híbrido
    _node(
        "hib_contratos_safra",
        "Contratos de Safra",
        "Híbrido Agricultura + Comércio: +4% no preço de venda e +4% de XP.",
        HYBRID,
        3,
        0,
        (_e(Stat.SELL_PRICE, 4), _e(Stat.XP_GAIN, 4)),
        branch_points=((_AGRO, 6), (_COM, 6)),
        angle=300,
    ),
    # ------------------------------------------------------------------- Pecuária
    _node(
        "pec_pasto_verde",
        "Pasto Verde",
        "+2% de produtos dos animais.",
        _PEC,
        1,
        -1,
        (_e(Stat.ANIMAL_YIELD, 2),),
    ),
    _node(
        "pec_cocho_farto",
        "Cocho Farto",
        "A ração rende 4% mais.",
        _PEC,
        1,
        0,
        (_e(Stat.FEED_EFFICIENCY, 4),),
    ),
    _node(
        "pec_manejo",
        "Manejo Gentil",
        "-2% no tempo de produção dos animais.",
        _PEC,
        1,
        1,
        (_e(Stat.ANIMAL_SPEED, -2),),
    ),
    _node(
        "pec_avicultor",
        "Avicultor",
        "Galinhas: +6% de ovos e -3% no tempo de produção.",
        _PEC,
        2,
        -1.5,
        (_e(Stat.ANIMAL_YIELD, 6, "galinha"), _e(Stat.ANIMAL_SPEED, -3, "galinha")),
        requires=("pec_pasto_verde",),
    ),
    _node(
        "pec_leiteiro",
        "Leiteiro",
        "Vacas: +6% de leite e -3% no tempo de produção.",
        _PEC,
        2,
        -0.5,
        (_e(Stat.ANIMAL_YIELD, 6, "vaca"), _e(Stat.ANIMAL_SPEED, -3, "vaca")),
        requires_any=("pec_pasto_verde", "pec_manejo"),
    ),
    _node(
        "pec_pastor",
        "Pastor",
        "Ovelhas: +6% de lã e -3% no tempo de produção.",
        _PEC,
        2,
        0.5,
        (_e(Stat.ANIMAL_YIELD, 6, "ovelha"), _e(Stat.ANIMAL_SPEED, -3, "ovelha")),
        requires_any=("pec_cocho_farto", "pec_manejo"),
    ),
    _node(
        "pec_silagem",
        "Silagem",
        "A ração rende 6% mais.",
        _PEC,
        2,
        1.5,
        (_e(Stat.FEED_EFFICIENCY, 6),),
        requires=("pec_cocho_farto",),
    ),
    _node(
        "pec_genetica",
        "Genética Selecionada",
        "+4% de produtos dos animais.",
        _PEC,
        3,
        -1,
        (_e(Stat.ANIMAL_YIELD, 4),),
        requires_any=("pec_avicultor", "pec_leiteiro"),
    ),
    _node(
        "pec_ordenha",
        "Rotina de Ordenha",
        "-5% no tempo de produção dos animais.",
        _PEC,
        3,
        0,
        (_e(Stat.ANIMAL_SPEED, -5),),
        requires_any=("pec_leiteiro", "pec_pastor"),
    ),
    _node(
        "pec_nutricao",
        "Nutrição Balanceada",
        "A ração rende 8% mais e +4% de XP.",
        _PEC,
        3,
        1,
        (_e(Stat.FEED_EFFICIENCY, 8), _e(Stat.XP_GAIN, 4)),
        requires_any=("pec_pastor", "pec_silagem"),
    ),
    _node(
        "pec_mestre_rebanho",
        "Mestre do Rebanho",
        "+8% de produtos e a ração rende 5% mais.",
        _PEC,
        4,
        -0.5,
        (_e(Stat.ANIMAL_YIELD, 8), _e(Stat.FEED_EFFICIENCY, 5)),
        requires_any=("pec_genetica", "pec_ordenha"),
        exclusive_group="pec_mestre",
    ),
    _node(
        "pec_mestre_manejo",
        "Mestre do Manejo",
        "-8% no tempo de produção e a ração rende 6% mais.",
        _PEC,
        4,
        0.5,
        (_e(Stat.ANIMAL_SPEED, -8), _e(Stat.FEED_EFFICIENCY, 6)),
        requires_any=("pec_ordenha", "pec_nutricao"),
        exclusive_group="pec_mestre",
    ),
    _node(
        "pec_fazenda_modelo",
        "Fazenda Modelo",
        "+8% de produtos, -4% no tempo de produção e +8% de XP.",
        _PEC,
        5,
        0,
        (_e(Stat.ANIMAL_YIELD, 8), _e(Stat.ANIMAL_SPEED, -4), _e(Stat.XP_GAIN, 8)),
        requires_any=("pec_mestre_rebanho", "pec_mestre_manejo"),
    ),
    # ------------------------------------------------------------------ Indústria
    _node(
        "ind_ferramentas",
        "Ferramentas Afiadas",
        "-2% no tempo de fabricação.",
        _IND,
        1,
        -1,
        (_e(Stat.PRODUCTION_TIME, -2),),
    ),
    _node(
        "ind_aproveitamento",
        "Aproveitamento",
        "2% de chance de um lote não gastar insumos.",
        _IND,
        1,
        0,
        (_e(Stat.PRODUCTION_SAVING, 2),),
    ),
    _node(
        "ind_boa_receita",
        "Boa Receita",
        "+2% de rendimento na fabricação.",
        _IND,
        1,
        1,
        (_e(Stat.PRODUCTION_YIELD, 2),),
    ),
    _node(
        "ind_moleiro",
        "Moleiro",
        "Moinho: -5% no tempo e +5% de rendimento.",
        _IND,
        2,
        -1.5,
        (_e(Stat.PRODUCTION_TIME, -5, "moinho"), _e(Stat.PRODUCTION_YIELD, 5, "moinho")),
        requires=("ind_ferramentas",),
    ),
    _node(
        "ind_padeiro",
        "Padeiro",
        "Padaria: -5% no tempo e +5% de rendimento.",
        _IND,
        2,
        -0.5,
        (_e(Stat.PRODUCTION_TIME, -5, "padaria"), _e(Stat.PRODUCTION_YIELD, 5, "padaria")),
        requires_any=("ind_ferramentas", "ind_boa_receita"),
    ),
    _node(
        "ind_queijeiro",
        "Queijeiro",
        "Queijaria: -5% no tempo e +5% de rendimento.",
        _IND,
        2,
        0.5,
        (_e(Stat.PRODUCTION_TIME, -5, "queijaria"), _e(Stat.PRODUCTION_YIELD, 5, "queijaria")),
        requires_any=("ind_boa_receita", "ind_aproveitamento"),
    ),
    _node(
        "ind_estoque",
        "Estoque Organizado",
        "4% de chance de um lote não gastar insumos.",
        _IND,
        2,
        1.5,
        (_e(Stat.PRODUCTION_SAVING, 4),),
        requires=("ind_aproveitamento",),
    ),
    _node(
        "ind_linha",
        "Linha de Produção",
        "-5% no tempo de fabricação.",
        _IND,
        3,
        -1,
        (_e(Stat.PRODUCTION_TIME, -5),),
        requires_any=("ind_moleiro", "ind_padeiro"),
    ),
    _node(
        "ind_otimizacao",
        "Otimização de Insumos",
        "5% de chance de um lote não gastar insumos.",
        _IND,
        3,
        0,
        (_e(Stat.PRODUCTION_SAVING, 5),),
        requires_any=("ind_padeiro", "ind_queijeiro", "ind_estoque"),
    ),
    _node(
        "ind_qualidade",
        "Controle de Qualidade",
        "+5% de rendimento na fabricação.",
        _IND,
        3,
        1,
        (_e(Stat.PRODUCTION_YIELD, 5),),
        requires_any=("ind_queijeiro", "ind_estoque"),
    ),
    _node(
        "ind_mestre_eficiencia",
        "Mestre da Eficiência",
        "6% de chance de lote grátis e -5% no tempo.",
        _IND,
        4,
        -0.5,
        (_e(Stat.PRODUCTION_SAVING, 6), _e(Stat.PRODUCTION_TIME, -5)),
        requires_any=("ind_linha", "ind_otimizacao"),
        exclusive_group="ind_mestre",
    ),
    _node(
        "ind_mestre_volume",
        "Mestre do Volume",
        "+8% de rendimento e -3% no tempo.",
        _IND,
        4,
        0.5,
        (_e(Stat.PRODUCTION_YIELD, 8), _e(Stat.PRODUCTION_TIME, -3)),
        requires_any=("ind_otimizacao", "ind_qualidade"),
        exclusive_group="ind_mestre",
    ),
    _node(
        "ind_fabrica",
        "Fábrica Lendária",
        "+8% de rendimento, 5% de lote grátis e -6% no tempo.",
        _IND,
        5,
        0,
        (_e(Stat.PRODUCTION_YIELD, 8), _e(Stat.PRODUCTION_SAVING, 5), _e(Stat.PRODUCTION_TIME, -6)),
        requires_any=("ind_mestre_eficiencia", "ind_mestre_volume"),
    ),
    # -------------------------------------------------------- Híbridos (novos)
    _node(
        "hib_laticinios",
        "Laticínios",
        "Híbrido Pecuária + Indústria: leite, queijo e manteiga valem +8% no mercado.",
        HYBRID,
        3,
        0,
        (
            _e(Stat.SELL_PRICE, 8, "leite"),
            _e(Stat.SELL_PRICE, 8, "queijo"),
            _e(Stat.SELL_PRICE, 8, "manteiga"),
        ),
        branch_points=((_PEC, 6), (_IND, 6)),
        angle=60,
    ),
    _node(
        "hib_feira_pecuaria",
        "Feira de Produtos",
        "Híbrido Comércio + Pecuária: ovos, leite e lã valem +8% no mercado.",
        HYBRID,
        3,
        0,
        (
            _e(Stat.SELL_PRICE, 8, "ovo"),
            _e(Stat.SELL_PRICE, 8, "leite"),
            _e(Stat.SELL_PRICE, 8, "la"),
        ),
        branch_points=((_COM, 6), (_PEC, 6)),
        angle=0,
    ),
)

NODES_BY_ID: dict[str, TalentNode] = {node.id: node for node in NODES}


def get_node(node_id: str) -> TalentNode | None:
    return NODES_BY_ID.get(node_id)


def get_branch(branch_id: str) -> Branch | None:
    return _BRANCH_BY_ID.get(branch_id)


def validate_catalog() -> list[str]:
    """Retorna problemas de consistência do catálogo (vazio = válido)."""
    problems: list[str] = []
    seen_positions: set[tuple[int, int]] = set()
    # Escopos aceitos: culturas, espécies, produtos (leite, pão...) e estações.
    scopes = set(CROPS) | set(ANIMALS) | {recipe.station for recipe in RECIPES.values()}
    scopes |= {animal.product_item.partition("_")[2] for animal in ANIMALS.values()}
    scopes |= {item_id.partition("_")[2] for item_id in PROCESSED_ITEMS}

    for node in NODES:
        if node.branch != HYBRID:
            branch = get_branch(node.branch)
            if branch is None or not branch.available:
                problems.append(f"{node.id}: ramo indisponível ou desconhecido ({node.branch})")
        for ref in (*node.requires, *node.requires_any):
            if ref not in NODES_BY_ID:
                problems.append(f"{node.id}: pré-requisito inexistente {ref}")
            elif NODES_BY_ID[ref].tier >= node.tier:
                problems.append(f"{node.id}: pré-requisito {ref} não é de camada inferior")
        if node.tier > 1 and not (node.requires or node.requires_any or node.branch_points):
            problems.append(f"{node.id}: sem pré-requisito")
        for effect in node.effects:
            if effect.stat not in IMPLEMENTED_STATS:
                problems.append(f"{node.id}: estatística não implementada {effect.stat}")
            if effect.scope is not None and effect.scope not in scopes:
                problems.append(f"{node.id}: escopo desconhecido {effect.scope}")
        if (node.x, node.y) in seen_positions:
            problems.append(f"{node.id}: posição duplicada")
        seen_positions.add((node.x, node.y))
    return problems
