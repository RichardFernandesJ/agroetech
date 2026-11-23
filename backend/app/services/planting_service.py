"""Sistema de plantação: plantar, listar e colher."""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.core.time import utcnow
from app.game.catalog import get_crop, get_item
from app.game.progression import PLANT_XP
from app.game.status import PlantingStatus
from app.models.planting import Planting
from app.models.property import Property
from app.repositories.planting_repository import PlantingRepository
from app.schemas.planting import PlantingCreate
from app.services.inventory_service import InventoryService
from app.services.production_service import ProductionService
from app.services.progress_service import ProgressService
from app.services.property_service import PropertyService


@dataclass(frozen=True, slots=True)
class HarvestOutcome:
    planting_id: uuid.UUID
    crop_id: str
    crop_name: str
    cycles_harvested: int
    product_item: str
    product_name: str
    product_quantity: int
    seed_item: str
    seed_name: str
    seed_quantity: int
    planting_status: PlantingStatus
    xp_gained: int = 0


class PlantingService:
    def __init__(
        self,
        session: AsyncSession,
        properties: PropertyService,
        plantings: PlantingRepository,
        inventory: InventoryService,
        production: ProductionService,
        progress: ProgressService,
    ) -> None:
        self.session = session
        self.properties = properties
        self.plantings = plantings
        self.inventory = inventory
        self.production = production
        self.progress = progress

    async def list_plantings(
        self,
        property_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> tuple[Property, Sequence[Planting]]:
        property_ = await self.properties.get_owned(property_id, owner_id)
        # Atualiza o estado (produção offline) antes de devolver ao cliente.
        await self.production.sync_property(property_)
        plantings = await self.plantings.list_by_property(property_.id)
        return property_, plantings

    async def plant(
        self,
        property_id: uuid.UUID,
        owner_id: uuid.UUID,
        payload: PlantingCreate,
    ) -> Planting:
        property_ = await self.properties.get_owned(property_id, owner_id)
        await self.production.sync_property(property_)

        crop = get_crop(payload.crop_id)
        if crop is None:
            raise NotFoundError("Cultura não encontrada no catálogo.")

        if payload.plot_index >= property_.plot_count:
            raise GameRuleError(
                f"Talhão inválido. Esta propriedade possui {property_.plot_count} talhões."
            )

        occupied = await self.plantings.get_active_on_plot(property_.id, payload.plot_index)
        if occupied is not None:
            raise ConflictError("Este talhão já está ocupado por outro plantio.")

        await self.inventory.consume(
            property_.id,
            crop.seed_item,
            1,
            label=f"sementes de {crop.name.lower()}",
        )

        now = utcnow()
        planting = Planting(
            property_id=property_.id,
            crop_id=crop.id,
            plot_index=payload.plot_index,
            planted_at=now,
            next_ready_at=now + timedelta(seconds=crop.grow_seconds),
            cycles_done=0,
            stored_cycles=0,
            status=PlantingStatus.GROWING.value,
        )
        await self.plantings.add(planting)
        await self.progress.grant(property_.owner_id, PLANT_XP)
        return planting

    async def harvest(
        self,
        planting_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> HarvestOutcome:
        planting = await self.plantings.get_owned(planting_id, owner_id)
        if planting is None:
            raise NotFoundError("Plantio não encontrado.")

        # Sincroniza antes de colher para considerar ciclos que amadureceram
        # enquanto o jogador estava offline.
        await self.production.sync_property(planting.property)
        return await self._harvest(planting, planting.property)

    async def harvest_all(
        self,
        property_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> tuple[Property, list[HarvestOutcome]]:
        property_ = await self.properties.get_owned(property_id, owner_id)
        await self.production.sync_property(property_)

        active_plantings = await self.plantings.list_by_property(property_.id)
        outcomes: list[HarvestOutcome] = []
        for planting in active_plantings:
            if planting.stored_cycles > 0:
                outcomes.append(await self._harvest(planting, property_))
        return property_, outcomes

    async def _harvest(self, planting: Planting, property_: Property) -> HarvestOutcome:
        crop = get_crop(planting.crop_id)
        if crop is None:
            raise NotFoundError("A cultura deste plantio não existe mais no catálogo.")

        if planting.stored_cycles <= 0:
            raise GameRuleError("Este plantio ainda não tem colheita pronta.")

        cycles = planting.stored_cycles
        product_quantity = cycles * crop.yield_quantity
        seed_quantity = cycles * crop.seed_yield

        await self.inventory.add(property_.id, crop.product_item, product_quantity)
        await self.inventory.add(property_.id, crop.seed_item, seed_quantity)

        planting.cycles_done += cycles
        planting.stored_cycles = 0
        if planting.cycles_done >= crop.max_cycles:
            planting.status = PlantingStatus.EXHAUSTED.value
        else:
            planting.status = PlantingStatus.GROWING.value

        await self.session.flush()

        grant = await self.progress.grant(property_.owner_id, cycles * crop.harvest_xp)

        product = get_item(crop.product_item)
        seed = get_item(crop.seed_item)

        return HarvestOutcome(
            planting_id=planting.id,
            crop_id=crop.id,
            crop_name=crop.name,
            cycles_harvested=cycles,
            product_item=crop.product_item,
            product_name=product.name if product else crop.name,
            product_quantity=product_quantity,
            seed_item=crop.seed_item,
            seed_name=seed.name if seed else crop.seed_item,
            seed_quantity=seed_quantity,
            planting_status=PlantingStatus(planting.status),
            xp_gained=grant.gained,
        )
