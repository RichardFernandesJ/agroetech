"""Catálogo de construções melhoráveis (conteúdo do jogo, versionado em código).

Cada construção tem níveis. O nível de uma construção nova pode ser 0
(ainda não construída). Os efeitos de um nível são o total vigente naquele
nível (não acumulam com os anteriores) e entram no motor de modificadores.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.game.modifiers import Effect, Stat


@dataclass(frozen=True, slots=True)
class BuildingLevel:
    level: int
    cost: int  # AGC para alcançar este nível
    min_player_level: int
    effects: tuple[Effect, ...] = ()
    plots: int | None = None  # total de talhões da propriedade neste nível
    capacity: int | None = None  # animais abrigados neste nível (abrigos)
    job_slots: int | None = None  # trabalhos de fabricação simultâneos (estações)


@dataclass(frozen=True, slots=True)
class BuildingDefinition:
    id: str
    name: str
    description: str
    initial_level: int
    levels: tuple[BuildingLevel, ...]

    @property
    def max_level(self) -> int:
        return self.levels[-1].level

    def level_info(self, level: int) -> BuildingLevel | None:
        return next((entry for entry in self.levels if entry.level == level), None)


BUILDINGS: dict[str, BuildingDefinition] = {
    "sede": BuildingDefinition(
        id="sede",
        name="Casa da Fazenda",
        description="A sede da ilha. Cada melhoria abre mais talhões para cultivar.",
        initial_level=1,
        levels=(
            BuildingLevel(level=1, cost=0, min_player_level=1, plots=6),
            BuildingLevel(level=2, cost=150, min_player_level=3, plots=8),
            BuildingLevel(level=3, cost=400, min_player_level=8, plots=10),
            BuildingLevel(level=4, cost=900, min_player_level=15, plots=12),
        ),
    ),
    "poco": BuildingDefinition(
        id="poco",
        name="Poço da Ilha",
        description="Irrigação para as lavouras: as plantas crescem mais rápido.",
        initial_level=0,
        levels=(
            BuildingLevel(
                level=1,
                cost=60,
                min_player_level=2,
                effects=(Effect(Stat.CROP_GROW_TIME, -200),),
            ),
            BuildingLevel(
                level=2,
                cost=200,
                min_player_level=6,
                effects=(Effect(Stat.CROP_GROW_TIME, -400),),
            ),
            BuildingLevel(
                level=3,
                cost=500,
                min_player_level=12,
                effects=(Effect(Stat.CROP_GROW_TIME, -600),),
            ),
        ),
    ),
}


# Abrigos de animais (veja game/animals.py). O estábulo abriga vacas e ovelhas.
BUILDINGS["galinheiro"] = BuildingDefinition(
    id="galinheiro",
    name="Galinheiro",
    description="Abriga galinhas. Cada melhoria aumenta quantas você pode criar.",
    initial_level=0,
    levels=(
        BuildingLevel(level=1, cost=80, min_player_level=2, capacity=3),
        BuildingLevel(level=2, cost=250, min_player_level=6, capacity=6),
        BuildingLevel(level=3, cost=600, min_player_level=12, capacity=10),
    ),
)

BUILDINGS["estabulo"] = BuildingDefinition(
    id="estabulo",
    name="Estábulo",
    description="Abriga vacas e ovelhas. Cada melhoria aumenta a lotação.",
    initial_level=0,
    levels=(
        BuildingLevel(level=1, cost=200, min_player_level=4, capacity=2),
        BuildingLevel(level=2, cost=500, min_player_level=9, capacity=4),
        BuildingLevel(level=3, cost=1100, min_player_level=16, capacity=6),
    ),
)


def _station(
    building_id: str,
    name: str,
    description: str,
    costs: tuple[int, int, int],
    player_levels: tuple[int, int, int],
) -> BuildingDefinition:
    """Estação de fabricação: +1 vaga por nível; níveis 2 e 3 também aceleram a produção."""
    speed = (0, -500, -1000)
    return BuildingDefinition(
        id=building_id,
        name=name,
        description=description,
        initial_level=0,
        levels=tuple(
            BuildingLevel(
                level=index + 1,
                cost=costs[index],
                min_player_level=player_levels[index],
                job_slots=index + 1,
                effects=(
                    (Effect(Stat.PRODUCTION_TIME, speed[index], building_id),)
                    if speed[index]
                    else ()
                ),
            )
            for index in range(3)
        ),
    )


BUILDINGS["moinho"] = _station(
    "moinho",
    "Moinho",
    "Mói o milho em farinha. Melhorias dão mais vagas e velocidade.",
    (150, 400, 900),
    (3, 8, 14),
)
BUILDINGS["padaria"] = _station(
    "padaria",
    "Padaria",
    "Assa pães e bolos. Melhorias dão mais vagas e velocidade.",
    (250, 600, 1300),
    (5, 10, 16),
)
BUILDINGS["queijaria"] = _station(
    "queijaria",
    "Queijaria",
    "Faz queijo e manteiga com o leite. Melhorias dão mais vagas e velocidade.",
    (300, 700, 1500),
    (6, 11, 17),
)


def get_building(building_id: str) -> BuildingDefinition | None:
    return BUILDINGS.get(building_id)


def effects_for_levels(levels: dict[str, int]) -> list[Effect]:
    """Efeitos vigentes dado o nível atual de cada construção da propriedade."""
    effects: list[Effect] = []
    for building_id, definition in BUILDINGS.items():
        info = definition.level_info(levels.get(building_id, definition.initial_level))
        if info is not None:
            effects.extend(info.effects)
    return effects


# Talhões da propriedade quando nenhuma melhoria foi feita (nível inicial da sede).
STARTING_PLOTS = BUILDINGS["sede"].level_info(BUILDINGS["sede"].initial_level).plots or 6  # type: ignore[union-attr]
