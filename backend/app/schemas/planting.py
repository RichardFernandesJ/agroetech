"""Schemas do sistema de plantação e colheita."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.game.status import PlantingStatus


class PlantingCreate(BaseModel):
    crop_id: str = Field(min_length=1, max_length=40, examples=["milho"])
    plot_index: int = Field(ge=0, examples=[0])


class PlantingRead(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    crop_id: str
    crop_name: str
    plot_index: int
    status: PlantingStatus
    planted_at: datetime
    next_ready_at: datetime
    cycles_done: int
    max_cycles: int
    stored_cycles: int
    seconds_until_ready: int | None
    expected_yield: int


class HarvestRead(BaseModel):
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


class HarvestAllRead(BaseModel):
    property_id: uuid.UUID
    harvests: list[HarvestRead]
    products: dict[str, int]
    seeds: dict[str, int]
