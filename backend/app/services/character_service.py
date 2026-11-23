"""Regras de criação e posição do personagem."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.game.world import DEFAULT_FACING, SPAWN_X, SPAWN_Y, is_position_inside_world
from app.models.character import Character
from app.models.property import Property
from app.models.user import User
from app.repositories.character_repository import CharacterRepository
from app.schemas.character import CharacterCreate, CharacterPositionUpdate
from app.schemas.property import PropertyCreate
from app.services.property_service import PropertyService


class CharacterService:
    def __init__(
        self,
        session: AsyncSession,
        characters: CharacterRepository,
        properties: PropertyService,
    ) -> None:
        self.session = session
        self.characters = characters
        self.properties = properties

    async def create(self, user: User, payload: CharacterCreate) -> Character:
        if await self.characters.get_by_user_id(user.id) is not None:
            raise ConflictError("Este jogador já possui um personagem.")

        property_ = await self._resolve_property(user, payload.property_id)
        appearance = payload.appearance

        character = Character(
            user_id=user.id,
            property_id=property_.id,
            name=payload.name,
            skin_tone=appearance.skin_tone,
            hair_style=appearance.hair_style,
            outfit_color=appearance.outfit_color,
            position_x=SPAWN_X,
            position_y=SPAWN_Y,
            facing=DEFAULT_FACING,
        )
        return await self.characters.add(character)

    async def get_by_user(self, user_id: uuid.UUID) -> Character:
        character = await self.characters.get_by_user_id(user_id)
        if character is None:
            raise NotFoundError("Nenhum personagem criado ainda.")
        return character

    async def update_position(
        self,
        user_id: uuid.UUID,
        payload: CharacterPositionUpdate,
    ) -> Character:
        character = await self.get_by_user(user_id)

        if not is_position_inside_world(payload.x, payload.y):
            raise GameRuleError("Posição fora dos limites do mapa.")

        character.position_x = payload.x
        character.position_y = payload.y
        character.facing = payload.facing
        await self.session.flush()
        return character

    async def _resolve_property(
        self,
        user: User,
        property_id: uuid.UUID | None,
    ) -> Property:
        if property_id is not None:
            property_ = await self.properties.get_owned(property_id, user.id)
            return property_

        owned = await self.properties.list_owned(user.id)
        if owned:
            return owned[0]

        # Onboarding do MVP: o primeiro personagem ganha uma fazenda inicial.
        return await self.properties.create(
            user.id,
            PropertyCreate(
                name=f"Fazenda de {user.username}",
                area_hectares=12.0,
                plot_count=settings.default_plots_per_property,
            ),
        )
