"""Schemas dos animais."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AnimalRead(BaseModel):
    id: uuid.UUID
    species: str
    species_name: str
    product_item: str
    product_name: str
    stored: int
    max_stored: int
    # Tempo por produto e bônus de produção vigentes neste animal (talentos).
    produce_seconds: int
    yield_bonus_bp: int
    is_fed: bool
    fed_seconds_left: int
    # Segundos até o próximo produto (None se está com fome ou com o estoque cheio).
    seconds_to_next: int | None
    fed_until: datetime | None


class HousingRead(BaseModel):
    building_id: str
    name: str
    level: int
    capacity: int
    used: int


class SpeciesRead(BaseModel):
    id: str
    name: str
    description: str
    housing: str
    price: int
    min_player_level: int
    produce_seconds: int
    product_item: str
    product_name: str
    sell_price: int
    feed_item: str
    feed_name: str
    feed_seconds: int
    max_feed_seconds: int
    owned: int
    can_buy: bool
    blocked_reason: str | None


class AnimalsStateRead(BaseModel):
    property_id: uuid.UUID
    player_level: int
    balance: int
    animals: list[AnimalRead]
    housings: list[HousingRead]
    species: list[SpeciesRead]
    # Preenchidos conforme a ação realizada.
    replayed: bool = False
    products: dict[str, int] = {}
    units_fed: dict[str, int] = {}
    xp_gained: int = 0


class BuyAnimalRequest(BaseModel):
    species: str = Field(min_length=1, max_length=30)


class FeedRequest(BaseModel):
    units: int = Field(default=1, ge=1, le=64)
