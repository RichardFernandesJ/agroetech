"""Rotas da fabricação (estações, receitas e trabalhos)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import CraftingServiceDep, CurrentUser
from app.schemas.crafting import (
    CraftingStateRead,
    JobRead,
    RecipeInputRead,
    RecipeRead,
    StartRequest,
    StationRead,
)
from app.services.crafting_service import CraftingState

router = APIRouter(prefix="/properties/{property_id}/crafting", tags=["Fabricação"])

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Chave única por intenção de produzir; reenvios não iniciam outro trabalho.",
    ),
]


def _to_read(state: CraftingState) -> CraftingStateRead:
    stations = [
        StationRead(
            building_id=view.definition.id,
            name=view.definition.name,
            level=view.level,
            job_slots=view.job_slots,
            used_slots=view.used_slots,
            time_bonus_bp=view.time_bonus_bp,
            jobs=[
                JobRead(
                    id=job.job.id,
                    recipe_id=job.job.recipe_id,
                    recipe_name=job.recipe.name if job.recipe else job.job.recipe_id,
                    batches=job.job.batches,
                    output_item=job.job.output_item,
                    output_name=job.output_name,
                    output_quantity=job.job.output_quantity,
                    started_at=job.job.started_at,
                    finish_at=job.job.finish_at,
                    seconds_left=job.seconds_left,
                    ready=job.ready,
                )
                for job in view.jobs
            ],
        )
        for view in state.stations
    ]
    recipes = [
        RecipeRead(
            id=view.recipe.id,
            name=view.recipe.name,
            description=view.recipe.description,
            station=view.recipe.station,
            inputs=[
                RecipeInputRead(item_id=i.item_id, name=i.name, per_batch=i.per_batch, have=i.have)
                for i in view.inputs
            ],
            output_item=view.recipe.output_item,
            output_name=view.output_name,
            output_quantity=view.recipe.output_quantity,
            duration_seconds=view.recipe.duration_seconds,
            min_player_level=view.recipe.min_player_level,
            xp=view.recipe.xp,
            max_batches=view.max_batches,
            can_craft=view.can_craft,
            blocked_reason=view.blocked_reason,
        )
        for view in state.recipes
    ]
    return CraftingStateRead(
        property_id=state.property.id,
        player_level=state.player_level,
        stations=stations,
        recipes=recipes,
        replayed=state.replayed,
        collected=state.collected,
        xp_gained=state.xp_gained,
    )


@router.get("", response_model=CraftingStateRead, summary="Estações, receitas e trabalhos")
async def get_crafting(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    crafting: CraftingServiceDep,
) -> CraftingStateRead:
    return _to_read(await crafting.state(current_user, property_id))


@router.post("/start", response_model=CraftingStateRead, summary="Inicia uma produção")
async def start_job(
    property_id: uuid.UUID,
    payload: StartRequest,
    current_user: CurrentUser,
    crafting: CraftingServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> CraftingStateRead:
    state = await crafting.start(
        current_user, property_id, payload.recipe_id, payload.batches, idempotency_key
    )
    return _to_read(state)


@router.post("/collect", response_model=CraftingStateRead, summary="Coleta os trabalhos prontos")
async def collect_jobs(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    crafting: CraftingServiceDep,
) -> CraftingStateRead:
    return _to_read(await crafting.collect(current_user, property_id))
