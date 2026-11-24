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
