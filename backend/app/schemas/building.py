"""Schemas das construções."""

import uuid

from pydantic import BaseModel

from app.schemas.talent import EffectRead


class BuildingLevelRead(BaseModel):
    level: int
    cost: int
    min_player_level: int
    plots: int | None
    capacity: int | None = None
    effects: list[EffectRead]


class BuildingCatalogRead(BaseModel):
    id: str
    name: str
    description: str
    initial_level: int
    max_level: int
    levels: list[BuildingLevelRead]


class BuildingRead(BaseModel):
    id: str
    name: str
    description: str
    level: int
    max_level: int
    current: BuildingLevelRead | None
    next: BuildingLevelRead | None
    can_upgrade: bool
    blocked_reason: str | None


class BuildingsStateRead(BaseModel):
    property_id: uuid.UUID
    plot_count: int
    player_level: int
    balance: int
    buildings: list[BuildingRead]
    # True quando a chave de idempotência já havia sido processada.
    replayed: bool = False
