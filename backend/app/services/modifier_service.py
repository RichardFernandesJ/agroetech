"""Reúne todas as fontes de bônus (talentos e construções) em um único ModifierSet.

As mecânicas (plantio, mercado...) só falam com este serviço; novas fontes
(guilda, território, equipamentos) entram aqui sem mexer nelas.
"""

import uuid

from app.game.buildings import effects_for_levels
from app.game.modifiers import ModifierSet
from app.repositories.building_repository import BuildingRepository
from app.services.talent_service import TalentService


class ModifierService:
    def __init__(self, talents: TalentService, buildings: BuildingRepository) -> None:
        self.talents = talents
        self.buildings = buildings

    async def for_property(self, user_id: uuid.UUID, property_id: uuid.UUID) -> ModifierSet:
        talent_modifiers = await self.talents.modifiers_for(user_id)
        levels = await self.buildings.levels_by_property(property_id)
        return ModifierSet([*talent_modifiers.effects, *effects_for_levels(levels)])
