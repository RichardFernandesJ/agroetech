"""Schemas de propriedades."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel


class PropertyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120, examples=["Fazenda Boa Vista"])
    area_hectares: float = Field(gt=0, le=100_000, examples=[12.5])
    plot_count: int = Field(default=6, ge=1, le=24, examples=[6])

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise ValueError("O nome da propriedade precisa ter ao menos 2 caracteres.")
        return cleaned


class PropertyRead(ORMModel):
    id: uuid.UUID
    name: str
    area_hectares: float
    plot_count: int
    created_at: datetime
    last_production_sync_at: datetime
