"""Rotas de propriedades."""

import uuid
from collections.abc import Sequence

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PropertyServiceDep
from app.models.property import Property
from app.schemas.property import PropertyCreate, PropertyRead

router = APIRouter(prefix="/properties", tags=["Propriedades"])


@router.post(
    "",
    response_model=PropertyRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma propriedade com kit inicial de sementes",
)
async def create_property(
    payload: PropertyCreate,
    current_user: CurrentUser,
    service: PropertyServiceDep,
) -> Property:
    return await service.create(current_user.id, payload)


@router.get(
    "",
    response_model=list[PropertyRead],
    summary="Lista as propriedades do jogador",
)
async def list_properties(
    current_user: CurrentUser,
    service: PropertyServiceDep,
) -> Sequence[Property]:
    return await service.list_owned(current_user.id)


@router.get(
    "/{property_id}",
    response_model=PropertyRead,
    summary="Detalha uma propriedade do jogador",
)
async def get_property(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    service: PropertyServiceDep,
) -> Property:
    return await service.get_owned(property_id, current_user.id)
