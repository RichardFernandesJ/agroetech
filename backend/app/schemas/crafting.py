"""Schemas da fabricação."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.game.recipes import MAX_BATCHES


class JobRead(BaseModel):
    id: uuid.UUID
    recipe_id: str
    recipe_name: str
    batches: int
    output_item: str
    output_name: str
    output_quantity: int
    started_at: datetime
    finish_at: datetime
    seconds_left: int
    ready: bool


class StationRead(BaseModel):
    building_id: str
    name: str
    level: int
    job_slots: int
    used_slots: int
    # Bônus (negativo = mais rápido) no tempo de produção desta estação, em pontos-base.
    time_bonus_bp: int
    jobs: list[JobRead]


class RecipeInputRead(BaseModel):
    item_id: str
    name: str
    per_batch: int
    have: int


class RecipeRead(BaseModel):
    id: str
    name: str
    description: str
    station: str
    inputs: list[RecipeInputRead]
    output_item: str
    output_name: str
    output_quantity: int
    duration_seconds: int
    min_player_level: int
    xp: int
    max_batches: int
    can_craft: bool
    blocked_reason: str | None


class CraftingStateRead(BaseModel):
    property_id: uuid.UUID
    player_level: int
    stations: list[StationRead]
    recipes: list[RecipeRead]
    # Preenchidos conforme a ação realizada.
    replayed: bool = False
    collected: dict[str, int] = {}
    xp_gained: int = 0


class StartRequest(BaseModel):
    recipe_id: str = Field(min_length=1, max_length=40)
    batches: int = Field(default=1, ge=1, le=MAX_BATCHES)
