"""Rotas públicas do catálogo (consumidas pelo frontend Phaser)."""

from fastapi import APIRouter

from app.api.v1.serializers import serialize_crop
from app.game.catalog import CROPS, ITEM_CATALOG
from app.schemas.catalog import CropRead, ItemRead

router = APIRouter(prefix="/catalog", tags=["Catálogo"])


@router.get("/crops", response_model=list[CropRead], summary="Lista as culturas disponíveis")
async def list_crops() -> list[CropRead]:
    return [serialize_crop(crop) for crop in CROPS.values()]


@router.get("/items", response_model=list[ItemRead], summary="Lista sementes e produtos")
async def list_items() -> list[ItemRead]:
    return [
        ItemRead(
            id=item.id,
            name=item.name,
            category=item.category,
            description=item.description,
        )
        for item in ITEM_CATALOG.values()
    ]
