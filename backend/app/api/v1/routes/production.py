"""Rota de sincronização da produção offline."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, ProductionServiceDep, PropertyServiceDep
from app.api.v1.serializers import serialize_sync_report
from app.schemas.production import OfflineSyncRead

router = APIRouter(
    prefix="/properties/{property_id}/production",
    tags=["Produção offline"],
)


@router.post(
    "/sync",
    response_model=OfflineSyncRead,
    summary="Simula o tempo offline e armazena as colheitas maduras",
)
async def sync_production(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    properties: PropertyServiceDep,
    production: ProductionServiceDep,
) -> OfflineSyncRead:
    property_ = await properties.get_owned(property_id, current_user.id)
    report = await production.sync_property(property_)
    return serialize_sync_report(report)
