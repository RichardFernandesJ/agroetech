"""Schemas do catálogo de culturas e itens."""

from pydantic import BaseModel


class CropRead(BaseModel):
    id: str
    name: str
    description: str
    grow_seconds: int
    yield_quantity: int
    seed_yield: int
    max_cycles: int
    seed_price: int
    sell_price: int
    seed_item: str
    product_item: str


class ItemRead(BaseModel):
    id: str
    name: str
    category: str
    description: str
