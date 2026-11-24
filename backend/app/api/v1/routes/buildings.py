"""Rotas das construções melhoráveis."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import BuildingServiceDep, CurrentUser
from app.game.buildings import BuildingLevel
from app.schemas.building import BuildingLevelRead, BuildingRead, BuildingsStateRead
from app.schemas.talent import EffectRead
from app.services.building_service import BuildingsState

router = APIRouter(prefix="/properties/{property_id}/buildings", tags=["Construções"])

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Chave única por intenção de melhoria; reenvios não cobram de novo.",
    ),
]


def level_to_read(info: BuildingLevel) -> BuildingLevelRead:
    return BuildingLevelRead(
        level=info.level,
        cost=info.cost,
        min_player_level=info.min_player_level,
        plots=info.plots,
        capacity=info.capacity,
        effects=[
            EffectRead(stat=effect.stat, value_bp=effect.value_bp, scope=effect.scope)
            for effect in info.effects
        ],
    )


def _to_state_read(state: BuildingsState) -> BuildingsStateRead:
    return BuildingsStateRead(
        property_id=state.property.id,
        plot_count=state.property.plot_count,
        player_level=state.player_level,
        balance=state.balance,
        replayed=state.replayed,
        buildings=[
            BuildingRead(
                id=view.definition.id,
                name=view.definition.name,
                description=view.definition.description,
                level=view.level,
                max_level=view.definition.max_level,
                current=level_to_read(view.current) if view.current else None,
                next=level_to_read(view.next) if view.next else None,
                can_upgrade=view.can_upgrade,
                blocked_reason=view.blocked_reason,
            )
            for view in state.buildings
        ],
    )


@router.get("", response_model=BuildingsStateRead, summary="Construções e próximas melhorias")
async def list_buildings(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    buildings: BuildingServiceDep,
) -> BuildingsStateRead:
    return _to_state_read(await buildings.state(current_user, property_id))


@router.post(
    "/{building_id}/upgrade",
    response_model=BuildingsStateRead,
    summary="Melhora uma construção com AgroCoin",
)
async def upgrade_building(
    property_id: uuid.UUID,
    building_id: str,
    current_user: CurrentUser,
    buildings: BuildingServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> BuildingsStateRead:
    state = await buildings.upgrade(current_user, property_id, building_id, idempotency_key)
    return _to_state_read(state)
