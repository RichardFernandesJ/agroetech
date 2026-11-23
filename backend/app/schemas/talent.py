"""Schemas da árvore de talentos."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class EffectRead(BaseModel):
    stat: str
    value_bp: int
    scope: str | None


class TalentNodeRead(BaseModel):
    id: str
    name: str
    description: str
    branch: str
    tier: int
    tier_name: str
    cost: int
    min_level: int
    requires: list[str]
    requires_any: list[str]
    branch_points: dict[str, int]
    exclusive_group: str | None
    effects: list[EffectRead]
    x: int
    y: int


class BranchRead(BaseModel):
    id: str
    name: str
    description: str
    available: bool
    angle: int


class TalentCatalogRead(BaseModel):
    center_x: int
    center_y: int
    branches: list[BranchRead]
    nodes: list[TalentNodeRead]


class PresetRead(BaseModel):
    id: uuid.UUID
    name: str
    slot: int
    is_active: bool
    node_ids: list[str]
    points_spent: int
    last_activated_at: datetime | None


class TalentStateRead(BaseModel):
    level: int
    points_total: int
    points_spent: int
    points_available: int
    preset_slots: int
    presets: list[PresetRead]
    active_preset_id: uuid.UUID | None
    switch_available_at: datetime | None
    reset_cost: int
    reset_is_free: bool
    build_locked: bool
    # Totais de bônus do preset ativo por estatística, em pontos-base (10.000 = 100%).
    modifiers: dict[str, int]


class AllocateRequest(BaseModel):
    node_id: str = Field(min_length=1, max_length=60)


class PresetName(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class ResetRead(BaseModel):
    cost: int
    state: TalentStateRead
