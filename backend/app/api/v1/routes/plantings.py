"""Rotas de plantação, colheita e produção offline."""

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PlantingServiceDep
from app.api.v1.serializers import (
    serialize_harvest,
    serialize_harvest_all,
    serialize_planting,
)
from app.core.time import utcnow
from app.schemas.planting import (
    HarvestAllRead,
    HarvestRead,
    PlantingCreate,
    PlantingRead,
)

router = APIRouter(tags=["Plantação"])


@router.get(
    "/properties/{property_id}/plantings",
    response_model=list[PlantingRead],
    summary="Lista os plantios (sincronizando a produção offline)",
)
async def list_plantings(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    service: PlantingServiceDep,
) -> list[PlantingRead]:
    _, plantings = await service.list_plantings(property_id, current_user.id)
    now = utcnow()
    return [serialize_planting(planting, now) for planting in plantings]


@router.post(
    "/properties/{property_id}/plantings",
    response_model=PlantingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Planta uma cultura em um talhão",
)
async def plant(
    property_id: uuid.UUID,
    payload: PlantingCreate,
    current_user: CurrentUser,
    service: PlantingServiceDep,
) -> PlantingRead:
    planting = await service.plant(property_id, current_user.id, payload)
    return serialize_planting(planting)


@router.post(
    "/properties/{property_id}/harvest",
    response_model=HarvestAllRead,
    summary="Colhe todos os plantios prontos da propriedade",
)
async def harvest_all(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    service: PlantingServiceDep,
) -> HarvestAllRead:
    property_, outcomes = await service.harvest_all(property_id, current_user.id)
    return serialize_harvest_all(property_.id, outcomes)


@router.post(
    "/plantings/{planting_id}/harvest",
    response_model=HarvestRead,
    summary="Colhe um plantio específico",
)
async def harvest(
    planting_id: uuid.UUID,
    current_user: CurrentUser,
    service: PlantingServiceDep,
) -> HarvestRead:
    outcome = await service.harvest(planting_id, current_user.id)
    return serialize_harvest(outcome)
