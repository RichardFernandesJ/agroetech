"""Schemas de personagem e posição no mundo."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.game.world import WORLD_HEIGHT, WORLD_WIDTH

SkinTone = Literal["light", "medium", "dark", "deep"]
HairStyle = Literal["short", "long", "bun", "cap"]
Facing = Literal["up", "down", "left", "right"]


class CharacterAppearance(BaseModel):
    skin_tone: SkinTone = "medium"
    hair_style: HairStyle = "short"
    outfit_color: str = Field(default="#3f7d4e", pattern=r"^#[0-9a-fA-F]{6}$")


class CharacterCreate(BaseModel):
    name: str = Field(min_length=3, max_length=20, examples=["Ana"])
    property_id: uuid.UUID | None = Field(
        default=None,
        description="Fazenda do personagem. Se omitida, usa a primeira ou cria uma inicial.",
    )
    appearance: CharacterAppearance = Field(default_factory=CharacterAppearance)

    @field_validator("name")
    @classmethod
    def name_must_be_valid(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 3:
            raise ValueError("O nome do personagem precisa ter ao menos 3 caracteres.")
        if not all(char.isalnum() or char in " ._-" for char in cleaned):
            raise ValueError("Use apenas letras, números, espaço, ponto, hífen ou sublinhado.")
        return cleaned


class CharacterPositionUpdate(BaseModel):
    x: float = Field(ge=0, le=WORLD_WIDTH)
    y: float = Field(ge=0, le=WORLD_HEIGHT)
    facing: Facing


class CharacterRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    property_id: uuid.UUID
    name: str
    appearance: CharacterAppearance
    position_x: float
    position_y: float
    facing: Facing
    created_at: datetime
