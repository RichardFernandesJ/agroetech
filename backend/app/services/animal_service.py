"""Animais: compra, alimentação, produção offline determinística e coleta.

A produção é calculada por ``game.animals.advance`` a cada acesso (nenhum
processo roda por jogador). Compra e coleta são atômicas; a compra é
idempotente por ``Idempotency-Key`` e usa a mesma carteira travada do mercado.
"""

import math
import uuid
from dataclasses import dataclass, field

from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.core.time import ensure_utc, utcnow
from app.game import animals as rules
from app.game.animals import ANIMALS, AnimalDefinition, get_animal
from app.game.buildings import BUILDINGS, get_building
from app.game.catalog import get_item
from app.game.modifiers import BP, Stat, scale, scaled_seconds, seeded_rng
from app.models.animal import Animal
from app.models.property import Property
from app.models.user import User
from app.repositories.animal_repository import AnimalRepository
from app.repositories.building_repository import BuildingRepository
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService
from app.services.modifier_service import ModifierService
from app.services.progress_service import ProgressService
from app.services.property_service import PropertyService
from app.services.wallet_service import WalletService

KIND_PURCHASE = "animal_purchase"


@dataclass(frozen=True, slots=True)
class AnimalView:
    animal: Animal
    definition: AnimalDefinition
    fed_seconds_left: int
    seconds_to_next: int | None
    produce_seconds: int  # já com o bônus de velocidade do animal
    max_stored: int
    yield_bp: int


@dataclass(frozen=True, slots=True)
class HousingView:
    building_id: str
    name: str
    level: int
    capacity: int
    used: int


@dataclass(frozen=True, slots=True)
class SpeciesView:
    definition: AnimalDefinition
    owned: int
    can_buy: bool
    blocked_reason: str | None


@dataclass(slots=True)
class AnimalsState:
    property: Property
    player_level: int
    balance: int
    animals: list[AnimalView]
    housings: list[HousingView]
    species: list[SpeciesView]
    replayed: bool = False
    products: dict[str, int] = field(default_factory=dict)
    units_fed: dict[str, int] = field(default_factory=dict)
    xp_gained: int = 0


def effective_produce_seconds(definition: AnimalDefinition, row: Animal) -> int:
    return scaled_seconds(definition.produce_seconds, row.speed_bp)


def effective_max_stored(definition: AnimalDefinition, row: Animal) -> int:
    """O estoque acompanha a velocidade: 8 h de produção, mesmo mais rápida."""
    return math.ceil(definition.max_feed_seconds / effective_produce_seconds(definition, row))


class AnimalService:
    def __init__(
        self,
        animals: AnimalRepository,
        buildings: BuildingRepository,
        inventory_repo: InventoryRepository,
        inventory: InventoryService,
        properties: PropertyService,
        progress: ProgressService,
        wallets: WalletService,
        modifiers: ModifierService,
    ) -> None:
        self.animals = animals
        self.buildings = buildings
        self.inventory_repo = inventory_repo
        self.inventory = inventory
        self.properties = properties
        self.progress = progress
        self.wallets = wallets
        self.modifiers = modifiers

    # ------------------------------------------------------------ consulta
    async def state(self, user: User, property_id: uuid.UUID) -> AnimalsState:
        property_ = await self.properties.get_owned(property_id, user.id)
        await self._synced(property_.id)
        return await self._build_state(user, property_)

    # -------------------------------------------------------------- compra
    async def buy(
        self,
        user: User,
        property_id: uuid.UUID,
        species_id: str,
        idempotency_key: str | None,
    ) -> AnimalsState:
        definition = get_animal(species_id)
        if definition is None:
            raise NotFoundError("Espécie não encontrada.")
        property_ = await self.properties.get_owned(property_id, user.id)

        wallet = await self.wallets.get_locked(user.id)
        if idempotency_key is not None:
            existing = await self.wallets.find_by_key(wallet, idempotency_key)
            if existing is not None:
                if (existing.kind, existing.item_id) != (KIND_PURCHASE, species_id):
                    raise ConflictError(
                        "Esta chave de idempotência já foi usada em outra operação."
                    )
                await self._synced(property_.id)
                state = await self._build_state(user, property_)
                state.replayed = True
                return state

        rows = await self._synced(property_.id, for_update=True)
        player_level = (await self.progress.describe(user.id)).level
        reason = await self._buy_blocker(definition, rows, player_level, wallet.balance, property_)
        if reason is not None:
            raise GameRuleError(reason)

        await self.wallets.apply(
            wallet,
            kind=KIND_PURCHASE,
            amount=-definition.price,
            item_id=species_id,
            quantity=1,
            unit_price=definition.price,
            idempotency_key=idempotency_key,
        )
        await self.animals.add(
            Animal(property_id=property_.id, species=species_id, last_sync_at=utcnow())
        )
        return await self._build_state(user, property_)

    # ------------------------------------------------------- alimentação
    async def feed(
        self,
        user: User,
        property_id: uuid.UUID,
        animal_id: uuid.UUID | None,
        units: int,
    ) -> AnimalsState:
        """Alimenta um animal (ou todos, com ``animal_id=None``) com até ``units`` porções cada."""
        property_ = await self.properties.get_owned(property_id, user.id)
        rows = await self._synced(property_.id, for_update=True)
        targets = [row for row in rows if animal_id is None or row.id == animal_id]
        if animal_id is not None and not targets:
            raise NotFoundError("Animal não encontrado.")
        if not targets:
            raise GameRuleError("Você ainda não tem animais.")

        now = utcnow()
        modifiers = await self.modifiers.for_property(user.id, property_.id)
        fed: dict[str, int] = {}
        out_of_feed = False
        for row in targets:
            definition = ANIMALS[row.species]
            stock = await self.inventory_repo.get_item_for_update(
                property_.id, definition.feed_item
            )
            available = stock.quantity if stock else 0
            if available <= 0:
                out_of_feed = True
                continue

            result = rules.feed(
                now=now,
                fed_until=row.fed_until,
                units=min(units, available),
                feed_seconds=definition.feed_seconds
                * (BP + modifiers.total_bp(Stat.FEED_EFFICIENCY, row.species))
                // BP,
                max_feed_seconds=definition.max_feed_seconds,
            )
            if result.units_used == 0:
                continue
            hungry = row.fed_until is None or ensure_utc(row.fed_until) <= now
            if hungry:
                # Nova rodada de produção: grava os bônus vigentes agora.
                row.speed_bp = modifiers.total_bp(Stat.ANIMAL_SPEED, row.species)
                row.yield_bp = modifiers.total_bp(Stat.ANIMAL_YIELD, row.species)
            await self.inventory.consume(
                property_.id,
                definition.feed_item,
                result.units_used,
                label=_item_name(definition.feed_item),
            )
            row.fed_until = result.fed_until
            fed[definition.feed_item] = fed.get(definition.feed_item, 0) + result.units_used

        await self.animals.session.flush()
        if not fed:
            if out_of_feed:
                raise GameRuleError("Sem ração no inventário (colha milho ou cenoura).")
            raise GameRuleError("Os animais já estão alimentados ao máximo.")

        state = await self._build_state(user, property_)
        state.units_fed = fed
        return state

    # -------------------------------------------------------------- coleta
    async def collect(self, user: User, property_id: uuid.UUID) -> AnimalsState:
        property_ = await self.properties.get_owned(property_id, user.id)
        rows = await self._synced(property_.id, for_update=True)

        products: dict[str, int] = {}
        base_xp = 0
        for row in rows:
            if row.stored <= 0:
                continue
            definition = ANIMALS[row.species]
            rng = seeded_rng("animal-collect", row.id, row.stored, int(row.progress_seconds))
            quantity = scale(row.stored, row.yield_bp, rng)
            products[definition.product_item] = products.get(definition.product_item, 0) + quantity
            base_xp += row.stored * definition.xp_per_product
            row.stored = 0

        if not products:
            raise GameRuleError("Nenhum produto pronto para coletar.")

        for item_id, quantity in products.items():
            await self.inventory.add(property_.id, item_id, quantity)

        modifiers = await self.modifiers.for_property(user.id, property_.id)
        rng = seeded_rng("collect", property_.id, utcnow().isoformat())
        xp = scale(base_xp, modifiers.total_bp(Stat.XP_GAIN), rng)
        grant = await self.progress.grant(user.id, xp)
        await self.animals.session.flush()

        state = await self._build_state(user, property_)
        state.products = products
        state.xp_gained = grant.gained
        return state

    # ------------------------------------------------------------ internos
    async def _synced(self, property_id: uuid.UUID, *, for_update: bool = False) -> list[Animal]:
        """Carrega os animais e contabiliza a produção até agora."""
        now = utcnow()
        rows = list(await self.animals.list_by_property(property_id, for_update=for_update))
        for row in rows:
            definition = ANIMALS[row.species]
            result = rules.advance(
                now=now,
                last_sync_at=row.last_sync_at,
                fed_until=row.fed_until,
                progress_seconds=row.progress_seconds,
                stored=row.stored,
                produce_seconds=effective_produce_seconds(definition, row),
                max_stored=effective_max_stored(definition, row),
            )
            row.progress_seconds = result.progress_seconds
            row.stored = result.stored
            row.last_sync_at = now
        await self.animals.session.flush()
        return rows

    async def _housing_capacity(self, property_id: uuid.UUID) -> dict[str, int]:
        levels = await self.buildings.levels_by_property(property_id)
        capacity: dict[str, int] = {}
        for building_id, definition in BUILDINGS.items():
            info = definition.level_info(levels.get(building_id, definition.initial_level))
            if info is not None and info.capacity is not None:
                capacity[building_id] = info.capacity
        return capacity

    async def _buy_blocker(
        self,
        definition: AnimalDefinition,
        rows: list[Animal],
        player_level: int,
        balance: int,
        property_: Property,
    ) -> str | None:
        if player_level < definition.min_player_level:
            return f"Requer nível de jogador {definition.min_player_level}."
        housing = get_building(definition.housing)
        capacity = (await self._housing_capacity(property_.id)).get(definition.housing, 0)
        if capacity == 0:
            name = housing.name if housing else definition.housing
            return f"Construa «{name}» para abrigar este animal."
        used = sum(1 for row in rows if ANIMALS[row.species].housing == definition.housing)
        if used >= capacity:
            name = housing.name if housing else definition.housing
            return f"{name} está lotado ({used}/{capacity}). Melhore a construção."
        if balance < definition.price:
            return f"Saldo insuficiente: faltam {definition.price - balance} AGC."
        return None

    async def _build_state(self, user: User, property_: Property) -> AnimalsState:
        now = utcnow()
        rows = list(await self.animals.list_by_property(property_.id))
        player_level = (await self.progress.describe(user.id)).level
        wallet = await self.wallets.get_or_create(user.id)
        capacity = await self._housing_capacity(property_.id)
        levels = await self.buildings.levels_by_property(property_.id)

        views: list[AnimalView] = []
        for row in rows:
            definition = ANIMALS[row.species]
            fed_left = 0
            if row.fed_until is not None:
                fed_left = max(0, int((ensure_utc(row.fed_until) - now).total_seconds()))
            produce = effective_produce_seconds(definition, row)
            cap = effective_max_stored(definition, row)
            to_next: int | None = None
            if fed_left > 0 and row.stored < cap:
                to_next = max(1, int(produce - row.progress_seconds))
            views.append(AnimalView(row, definition, fed_left, to_next, produce, cap, row.yield_bp))

        housings: list[HousingView] = []
        for building_id, cap in capacity.items():
            building = BUILDINGS[building_id]
            used = sum(1 for row in rows if ANIMALS[row.species].housing == building_id)
            housings.append(
                HousingView(building_id, building.name, levels.get(building_id, 0), cap, used)
            )
        # Construções de abrigo ainda não construídas também aparecem (capacidade 0).
        for definition in ANIMALS.values():
            if definition.housing not in capacity and get_building(definition.housing):
                if not any(h.building_id == definition.housing for h in housings):
                    building = BUILDINGS[definition.housing]
                    housings.append(HousingView(building.id, building.name, 0, 0, 0))

        species: list[SpeciesView] = []
        for definition in ANIMALS.values():
            reason = await self._buy_blocker(
                definition, rows, player_level, wallet.balance, property_
            )
            owned = sum(1 for row in rows if row.species == definition.id)
            species.append(SpeciesView(definition, owned, reason is None, reason))

        return AnimalsState(
            property=property_,
            player_level=player_level,
            balance=wallet.balance,
            animals=views,
            housings=housings,
            species=species,
        )


def _item_name(item_id: str) -> str:
    item = get_item(item_id)
    return item.name.lower() if item else item_id
