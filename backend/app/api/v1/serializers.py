"""Conversão de entidades/resultados de domínio para schemas de resposta."""

import math
import uuid
from collections.abc import Sequence
from datetime import datetime

from app.core.time import ensure_utc, utcnow
from app.game.catalog import CropDefinition, get_crop, get_item
from app.game.status import PlantingStatus
from app.models.character import Character
from app.models.inventory import InventoryItem
from app.models.planting import Planting
from app.schemas.catalog import CropRead, ItemRead
from app.schemas.character import CharacterAppearance, CharacterRead
from app.schemas.inventory import InventoryItemRead, InventoryRead
from app.schemas.planting import HarvestAllRead, HarvestRead, PlantingRead
from app.schemas.production import OfflineSyncRead
from app.services.planting_service import HarvestOutcome
from app.services.production_service import OfflineSyncReport


def serialize_crop(crop: CropDefinition) -> CropRead:
    return CropRead(
        id=crop.id,
        name=crop.name,
        description=crop.description,
        grow_seconds=crop.grow_seconds,
        yield_quantity=crop.yield_quantity,
        seed_yield=crop.seed_yield,
        max_cycles=crop.max_cycles,
        seed_price=crop.seed_price,
        sell_price=crop.sell_price,
        harvest_xp=crop.harvest_xp,
        seed_item=crop.seed_item,
        product_item=crop.product_item,
    )


def serialize_character(character: Character) -> CharacterRead:
    return CharacterRead(
        id=character.id,
        user_id=character.user_id,
        property_id=character.property_id,
        name=character.name,
        appearance=CharacterAppearance(
            skin_tone=character.skin_tone,
            hair_style=character.hair_style,
            outfit_color=character.outfit_color,
        ),
        position_x=character.position_x,
        position_y=character.position_y,
        facing=character.facing,
        created_at=character.created_at,
    )


def serialize_item(item_id: str) -> ItemRead | None:
    item = get_item(item_id)
    if item is None:
        return None
    return ItemRead(
        id=item.id,
        name=item.name,
        category=item.category,
        description=item.description,
    )


def serialize_inventory(
    property_id: uuid.UUID,
    items: Sequence[InventoryItem],
) -> InventoryRead:
    rows: list[InventoryItemRead] = []
    for item in items:
        metadata = get_item(item.item_id)
        rows.append(
            InventoryItemRead(
                item_id=item.item_id,
                name=metadata.name if metadata else item.item_id,
                category=metadata.category if metadata else "unknown",
                description=metadata.description if metadata else "",
                quantity=item.quantity,
            )
        )
    return InventoryRead(property_id=property_id, items=rows)


def serialize_planting(planting: Planting, now: datetime | None = None) -> PlantingRead:
    crop = get_crop(planting.crop_id)
    status = PlantingStatus(planting.status)
    now = ensure_utc(now) if now is not None else utcnow()
    next_ready_at = ensure_utc(planting.next_ready_at)

    if status is PlantingStatus.READY:
        seconds_until_ready: int | None = 0
    elif status is PlantingStatus.EXHAUSTED:
        seconds_until_ready = None
    else:
        seconds_until_ready = max(0, math.ceil((next_ready_at - now).total_seconds()))

    if crop is None:
        crop_name = planting.crop_id
        max_cycles = 0
        expected_yield = 0
    else:
        crop_name = crop.name
        max_cycles = crop.max_cycles
        expected_yield = (
            planting.stored_cycles * crop.yield_quantity
            if planting.stored_cycles > 0
            else crop.yield_quantity
        )

    return PlantingRead(
        id=planting.id,
        property_id=planting.property_id,
        crop_id=planting.crop_id,
        crop_name=crop_name,
        plot_index=planting.plot_index,
        status=status,
        planted_at=planting.planted_at,
        next_ready_at=planting.next_ready_at,
        cycles_done=planting.cycles_done,
        max_cycles=max_cycles,
        stored_cycles=planting.stored_cycles,
        seconds_until_ready=seconds_until_ready,
        expected_yield=expected_yield,
    )


def serialize_harvest(outcome: HarvestOutcome) -> HarvestRead:
    return HarvestRead(
        planting_id=outcome.planting_id,
        crop_id=outcome.crop_id,
        crop_name=outcome.crop_name,
        cycles_harvested=outcome.cycles_harvested,
        product_item=outcome.product_item,
        product_name=outcome.product_name,
        product_quantity=outcome.product_quantity,
        seed_item=outcome.seed_item,
        seed_name=outcome.seed_name,
        seed_quantity=outcome.seed_quantity,
        planting_status=outcome.planting_status,
        xp_gained=outcome.xp_gained,
    )


def serialize_harvest_all(
    property_id: uuid.UUID,
    outcomes: Sequence[HarvestOutcome],
) -> HarvestAllRead:
    products: dict[str, int] = {}
    seeds: dict[str, int] = {}
    for outcome in outcomes:
        products[outcome.product_item] = (
            products.get(outcome.product_item, 0) + outcome.product_quantity
        )
        seeds[outcome.seed_item] = seeds.get(outcome.seed_item, 0) + outcome.seed_quantity

    return HarvestAllRead(
        property_id=property_id,
        harvests=[serialize_harvest(outcome) for outcome in outcomes],
        products=products,
        seeds=seeds,
        xp_gained=sum(outcome.xp_gained for outcome in outcomes),
    )


def serialize_sync_report(report: OfflineSyncReport) -> OfflineSyncRead:
    return OfflineSyncRead(
        property_id=report.property_id,
        synced_at=report.synced_at,
        window_start=report.window_start,
        offline_seconds=report.offline_seconds,
        plantings_synced=report.plantings_synced,
        cycles_stored=report.cycles_stored,
        ready_plantings=report.ready_plantings,
    )
