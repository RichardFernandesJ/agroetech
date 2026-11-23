"""Rotas do personagem do jogador."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CharacterServiceDep, CurrentUser
from app.api.v1.serializers import serialize_character
from app.schemas.character import CharacterCreate, CharacterPositionUpdate, CharacterRead

router = APIRouter(prefix="/characters", tags=["Personagem"])


@router.post(
    "",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cria o personagem do jogador (e uma fazenda inicial, se necessário)",
)
async def create_character(
    payload: CharacterCreate,
    current_user: CurrentUser,
    service: CharacterServiceDep,
) -> CharacterRead:
    character = await service.create(current_user, payload)
    return serialize_character(character)


@router.get(
    "/me",
    response_model=CharacterRead,
    summary="Retorna o personagem do jogador autenticado",
)
async def get_my_character(
    current_user: CurrentUser,
    service: CharacterServiceDep,
) -> CharacterRead:
    character = await service.get_by_user(current_user.id)
    return serialize_character(character)


@router.patch(
    "/me/position",
    response_model=CharacterRead,
    summary="Persiste a posição do personagem no mapa",
)
async def update_my_position(
    payload: CharacterPositionUpdate,
    current_user: CurrentUser,
    service: CharacterServiceDep,
) -> CharacterRead:
    character = await service.update_position(current_user.id, payload)
    return serialize_character(character)
