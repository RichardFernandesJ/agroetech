"""Regras de cadastro e consulta de propriedades."""

import uuid
from collections.abc import Sequence

from app.core.config import settings
from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.core.time import utcnow
from app.game.buildings import STARTING_PLOTS
from app.game.catalog import STARTER_SEEDS
from app.models.property import Property
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyCreate


class PropertyService:
    def __init__(
        self,
        properties: PropertyRepository,
        inventory: InventoryRepository,
    ) -> None:
        self.properties = properties
        self.inventory = inventory

    async def create(self, owner_id: uuid.UUID, payload: PropertyCreate) -> Property:
        if payload.plot_count > settings.max_plots_per_property:
            raise GameRuleError(
                f"Uma propriedade pode ter no máximo {settings.max_plots_per_property} talhões."
            )

        if payload.plot_count > STARTING_PLOTS:
            raise GameRuleError(
                f"Uma fazenda nova começa com {STARTING_PLOTS} talhões; "
                "mais talhões vêm da melhoria da Casa da Fazenda."
            )
        if await self.properties.list_by_owner(owner_id):
            raise ConflictError("Você já possui uma fazenda.")

        property_ = Property(
            owner_id=owner_id,
            name=payload.name,
            area_hectares=payload.area_hectares,
            plot_count=STARTING_PLOTS,
            last_production_sync_at=utcnow(),
        )
        await self.properties.add(property_)

        # Kit inicial: permite plantar e iniciar o ciclo de produção.
        for item_id, quantity in STARTER_SEEDS.items():
            await self.inventory.add_quantity(property_.id, item_id, quantity)

        return property_

    async def list_owned(self, owner_id: uuid.UUID) -> Sequence[Property]:
        return await self.properties.list_by_owner(owner_id)

    async def get_owned(self, property_id: uuid.UUID, owner_id: uuid.UUID) -> Property:
        property_ = await self.properties.get_owned(property_id, owner_id)
        if property_ is None:
            # 404 (e não 403) para não revelar a existência de fazendas alheias.
            raise NotFoundError("Propriedade não encontrada.")
        return property_
