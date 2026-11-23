"""Rotas da árvore de talentos."""

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, TalentServiceDep
from app.schemas.talent import (
    AllocateRequest,
    PresetName,
    PresetRead,
    ResetRead,
    TalentStateRead,
)
from app.services.talent_service import TalentState

router = APIRouter(prefix="/talents", tags=["Talentos"])


def _to_state_read(state: TalentState) -> TalentStateRead:
    active = next((view for view in state.presets if view.preset.is_active), None)
    return TalentStateRead(
        level=state.level,
        points_total=state.points_total,
        points_spent=state.points_spent,
        points_available=state.points_available,
        preset_slots=state.preset_slots,
        presets=[
            PresetRead(
                id=view.preset.id,
                name=view.preset.name,
                slot=view.preset.slot,
                is_active=view.preset.is_active,
                node_ids=list(view.node_ids),
                points_spent=view.points_spent,
                last_activated_at=view.preset.last_activated_at,
            )
            for view in state.presets
        ],
        active_preset_id=active.preset.id if active else None,
        switch_available_at=state.switch_available_at,
        reset_cost=state.reset_cost,
        reset_is_free=state.reset_is_free,
        build_locked=state.build_locked,
        modifiers=state.modifiers,
    )


@router.get("", response_model=TalentStateRead, summary="Pontos, presets e bônus do jogador")
async def get_talents(current_user: CurrentUser, talents: TalentServiceDep) -> TalentStateRead:
    return _to_state_read(await talents.state(current_user.id))


@router.post("/allocate", response_model=TalentStateRead, summary="Adquire um talento")
async def allocate(
    payload: AllocateRequest,
    current_user: CurrentUser,
    talents: TalentServiceDep,
) -> TalentStateRead:
    await talents.allocate(current_user.id, payload.node_id)
    return _to_state_read(await talents.state(current_user.id))


@router.post("/reset", response_model=ResetRead, summary="Redefine os talentos do preset ativo")
async def reset(current_user: CurrentUser, talents: TalentServiceDep) -> ResetRead:
    cost = await talents.reset_active(current_user.id)
    return ResetRead(cost=cost, state=_to_state_read(await talents.state(current_user.id)))


@router.post(
    "/presets",
    response_model=TalentStateRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria um preset",
)
async def create_preset(
    payload: PresetName,
    current_user: CurrentUser,
    talents: TalentServiceDep,
) -> TalentStateRead:
    await talents.create_preset(current_user.id, payload.name)
    return _to_state_read(await talents.state(current_user.id))


@router.patch("/presets/{preset_id}", response_model=TalentStateRead, summary="Renomeia um preset")
async def rename_preset(
    preset_id: uuid.UUID,
    payload: PresetName,
    current_user: CurrentUser,
    talents: TalentServiceDep,
) -> TalentStateRead:
    await talents.rename_preset(current_user.id, preset_id, payload.name)
    return _to_state_read(await talents.state(current_user.id))


@router.delete("/presets/{preset_id}", response_model=TalentStateRead, summary="Exclui um preset")
async def delete_preset(
    preset_id: uuid.UUID,
    current_user: CurrentUser,
    talents: TalentServiceDep,
) -> TalentStateRead:
    await talents.delete_preset(current_user.id, preset_id)
    return _to_state_read(await talents.state(current_user.id))


@router.post(
    "/presets/{preset_id}/activate",
    response_model=TalentStateRead,
    summary="Ativa um preset (respeita a recarga de troca)",
)
async def activate_preset(
    preset_id: uuid.UUID,
    current_user: CurrentUser,
    talents: TalentServiceDep,
) -> TalentStateRead:
    await talents.activate_preset(current_user.id, preset_id)
    return _to_state_read(await talents.state(current_user.id))
