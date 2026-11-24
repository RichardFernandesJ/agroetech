"""Construções melhoráveis: consulta de estado e melhoria paga em AgroCoin.

A melhoria é atômica (saldo, nível e talhões na mesma transação), travada pela
linha da carteira e idempotente por ``Idempotency-Key``.
"""

import uuid
from dataclasses import dataclass

from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.game.buildings import BUILDINGS, BuildingDefinition, BuildingLevel, get_building
from app.models.building import Building
from app.models.property import Property
from app.models.user import User
from app.repositories.building_repository import BuildingRepository
from app.services.progress_service import ProgressService
from app.services.property_service import PropertyService
from app.services.wallet_service import WalletService

KIND_UPGRADE = "building_upgrade"


@dataclass(frozen=True, slots=True)
class BuildingView:
    definition: BuildingDefinition
    level: int
    current: BuildingLevel | None
    next: BuildingLevel | None
    can_upgrade: bool
    blocked_reason: str | None


@dataclass(frozen=True, slots=True)
class BuildingsState:
    property: Property
    player_level: int
    balance: int
    buildings: tuple[BuildingView, ...]
    replayed: bool = False


class BuildingService:
    def __init__(
        self,
        buildings: BuildingRepository,
        properties: PropertyService,
        progress: ProgressService,
        wallets: WalletService,
    ) -> None:
        self.buildings = buildings
        self.properties = properties
        self.progress = progress
        self.wallets = wallets

    async def state(self, user: User, property_id: uuid.UUID) -> BuildingsState:
        property_ = await self.properties.get_owned(property_id, user.id)
        return await self._build_state(user, property_)

    async def upgrade(
        self,
        user: User,
        property_id: uuid.UUID,
        building_id: str,
        idempotency_key: str | None,
    ) -> BuildingsState:
        definition = get_building(building_id)
        if definition is None:
            raise NotFoundError("Construção não encontrada.")
        property_ = await self.properties.get_owned(property_id, user.id)

        wallet = await self.wallets.get_locked(user.id)
        if idempotency_key is not None:
            existing = await self.wallets.find_by_key(wallet, idempotency_key)
            if existing is not None:
                if (existing.kind, existing.item_id) != (KIND_UPGRADE, building_id):
                    raise ConflictError(
                        "Esta chave de idempotência já foi usada em outra operação."
                    )
                state = await self._build_state(user, property_)
                return BuildingsState(
                    property=state.property,
                    player_level=state.player_level,
                    balance=state.balance,
                    buildings=state.buildings,
                    replayed=True,
                )

        row = await self.buildings.get_for_property(property_.id, building_id, for_update=True)
        current_level = row.level if row else definition.initial_level
        target = definition.level_info(current_level + 1)
        if target is None:
            raise GameRuleError(f"{definition.name} já está no nível máximo.")

        player_level = (await self.progress.describe(user.id)).level
        if player_level < target.min_player_level:
            raise GameRuleError(f"Requer nível de jogador {target.min_player_level}.")

        await self.wallets.apply(
            wallet,
            kind=KIND_UPGRADE,
            amount=-target.cost,
            item_id=building_id,
            quantity=target.level,
            unit_price=target.cost,
            idempotency_key=idempotency_key,
        )

        if row is None:
            await self.buildings.add(
                Building(property_id=property_.id, building_id=building_id, level=target.level)
            )
        else:
            row.level = target.level

        if target.plots is not None:
            property_.plot_count = max(property_.plot_count, target.plots)
        await self.buildings.session.flush()

        return await self._build_state(user, property_)

    async def _build_state(self, user: User, property_: Property) -> BuildingsState:
        levels = await self.buildings.levels_by_property(property_.id)
        player_level = (await self.progress.describe(user.id)).level
        wallet = await self.wallets.get_or_create(user.id)

        views: list[BuildingView] = []
        for definition in BUILDINGS.values():
            level = levels.get(definition.id, definition.initial_level)
            target = definition.level_info(level + 1)
            reason: str | None = None
            if target is None:
                reason = "Nível máximo alcançado."
            elif player_level < target.min_player_level:
                reason = f"Requer nível de jogador {target.min_player_level}."
            elif wallet.balance < target.cost:
                reason = f"Saldo insuficiente: faltam {target.cost - wallet.balance} AGC."
            views.append(
                BuildingView(
                    definition=definition,
                    level=level,
                    current=definition.level_info(level),
                    next=target,
                    can_upgrade=reason is None,
                    blocked_reason=reason,
                )
            )
        return BuildingsState(
            property=property_,
            player_level=player_level,
            balance=wallet.balance,
            buildings=tuple(views),
        )
