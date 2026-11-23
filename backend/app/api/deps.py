"""Dependências compartilhadas da API (injeção de dependência)."""

import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, InvalidTokenError
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories.character_repository import CharacterRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.planting_repository import PlantingRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.talent_repository import TalentRepository
from app.repositories.user_repository import UserRepository
from app.repositories.wallet_repository import WalletRepository
from app.services.auth_service import AuthService
from app.services.character_service import CharacterService
from app.services.inventory_service import InventoryService
from app.services.market_service import MarketService
from app.services.planting_service import PlantingService
from app.services.production_service import ProductionService
from app.services.progress_service import ProgressService
from app.services.property_service import PropertyService
from app.services.talent_service import TalentService
from app.services.wallet_service import WalletService

bearer_scheme = HTTPBearer(
    auto_error=False,
    description="Token JWT obtido em POST /api/v1/auth/login",
)

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise AuthenticationError("Token de acesso ausente.")

    payload = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTokenError("Token inválido.") from exc

    user = await UserRepository(db).get_by_id(user_id)
    if user is None:
        raise InvalidTokenError("O usuário deste token não existe mais.")
    if not user.is_active:
        raise AuthenticationError("Esta conta está desativada.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserRepository(db))


def get_property_service(db: DbSession) -> PropertyService:
    return PropertyService(PropertyRepository(db), InventoryRepository(db))


def get_inventory_service(db: DbSession) -> InventoryService:
    return InventoryService(db, InventoryRepository(db))


def get_wallet_service(db: DbSession) -> WalletService:
    return WalletService(db, WalletRepository(db))


def get_progress_service(db: DbSession) -> ProgressService:
    return ProgressService(db, ProgressRepository(db))


def get_talent_service(db: DbSession) -> TalentService:
    return TalentService(
        TalentRepository(db),
        ProgressService(db, ProgressRepository(db)),
        WalletService(db, WalletRepository(db)),
    )


def get_market_service(
    db: DbSession,
    properties: Annotated[PropertyService, Depends(get_property_service)],
    inventory: Annotated[InventoryService, Depends(get_inventory_service)],
    wallets: Annotated[WalletService, Depends(get_wallet_service)],
    talents: Annotated[TalentService, Depends(get_talent_service)],
) -> MarketService:
    return MarketService(properties, inventory, wallets, talents)


def get_character_service(
    db: DbSession,
    properties: Annotated[PropertyService, Depends(get_property_service)],
) -> CharacterService:
    return CharacterService(db, CharacterRepository(db), properties)


def get_production_service(db: DbSession) -> ProductionService:
    return ProductionService(db, PlantingRepository(db))


def get_planting_service(
    db: DbSession,
    production: Annotated[ProductionService, Depends(get_production_service)],
) -> PlantingService:
    return PlantingService(
        session=db,
        properties=PropertyService(PropertyRepository(db), InventoryRepository(db)),
        plantings=PlantingRepository(db),
        inventory=InventoryService(db, InventoryRepository(db)),
        production=production,
        progress=ProgressService(db, ProgressRepository(db)),
        talents=get_talent_service(db),
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
PropertyServiceDep = Annotated[PropertyService, Depends(get_property_service)]
InventoryServiceDep = Annotated[InventoryService, Depends(get_inventory_service)]
ProductionServiceDep = Annotated[ProductionService, Depends(get_production_service)]
PlantingServiceDep = Annotated[PlantingService, Depends(get_planting_service)]
CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]
WalletServiceDep = Annotated[WalletService, Depends(get_wallet_service)]
MarketServiceDep = Annotated[MarketService, Depends(get_market_service)]
ProgressServiceDep = Annotated[ProgressService, Depends(get_progress_service)]
TalentServiceDep = Annotated[TalentService, Depends(get_talent_service)]
