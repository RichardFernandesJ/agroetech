"""Fabricação: estações, receitas, trabalhos com duração e coleta.

Cada trabalho consome os insumos ao iniciar e guarda, no próprio registro, o
horário de término e a quantidade de saída (já com os bônus vigentes). Assim o
resultado é determinístico, funciona offline e não muda se o jogador trocar de
talentos depois. O progresso é calculado pelos timestamps (sem processos).
"""

import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from app.core.exceptions import GameRuleError, NotFoundError
from app.core.time import ensure_utc, utcnow
from app.game.buildings import BUILDINGS, BuildingDefinition, get_building
from app.game.catalog import get_item
from app.game.modifiers import Stat, scale, scaled_seconds, seeded_rng
from app.game.recipes import MAX_BATCHES, RECIPES, RecipeDefinition, get_recipe
from app.models.production_job import ProductionJob
from app.models.property import Property
from app.models.user import User
from app.repositories.building_repository import BuildingRepository
from app.repositories.inventory_repository import InventoryRepository
from app.repositories.production_job_repository import ProductionJobRepository
from app.services.inventory_service import InventoryService
from app.services.modifier_service import ModifierService
from app.services.progress_service import ProgressService
from app.services.property_service import PropertyService


@dataclass(frozen=True, slots=True)
class JobView:
    job: ProductionJob
    recipe: RecipeDefinition | None
    output_name: str
    seconds_left: int
    ready: bool


@dataclass(frozen=True, slots=True)
class StationView:
    definition: BuildingDefinition
    level: int
    job_slots: int
    used_slots: int
    time_bonus_bp: int
    jobs: list[JobView]


@dataclass(frozen=True, slots=True)
class InputView:
    item_id: str
    name: str
    per_batch: int
    have: int


@dataclass(frozen=True, slots=True)
class RecipeView:
    recipe: RecipeDefinition
    output_name: str
    inputs: list[InputView]
    max_batches: int
    can_craft: bool
    blocked_reason: str | None


@dataclass(slots=True)
class CraftingState:
    property: Property
    player_level: int
    stations: list[StationView]
    recipes: list[RecipeView]
    replayed: bool = False
    collected: dict[str, int] = field(default_factory=dict)
    xp_gained: int = 0


def _item_name(item_id: str) -> str:
    item = get_item(item_id)
    return item.name if item else item_id


class CraftingService:
    def __init__(
        self,
        jobs: ProductionJobRepository,
        buildings: BuildingRepository,
        inventory_repo: InventoryRepository,
        inventory: InventoryService,
        properties: PropertyService,
        progress: ProgressService,
        modifiers: ModifierService,
    ) -> None:
        self.jobs = jobs
        self.buildings = buildings
        self.inventory_repo = inventory_repo
        self.inventory = inventory
        self.properties = properties
        self.progress = progress
        self.modifiers = modifiers

    # ------------------------------------------------------------ consulta
    async def state(self, user: User, property_id: uuid.UUID) -> CraftingState:
        property_ = await self.properties.get_owned(property_id, user.id)
        return await self._build_state(user, property_)

    # --------------------------------------------------------------- início
    async def start(
        self,
        user: User,
        property_id: uuid.UUID,
        recipe_id: str,
        batches: int,
        idempotency_key: str | None,
    ) -> CraftingState:
        recipe = get_recipe(recipe_id)
        if recipe is None:
            raise NotFoundError("Receita não encontrada.")
        if not 1 <= batches <= MAX_BATCHES:
            raise GameRuleError(f"Escolha de 1 a {MAX_BATCHES} lotes.")
        property_ = await self.properties.get_owned(property_id, user.id)

        await self.jobs.lock_property(property_.id)
        if idempotency_key is not None:
            existing = await self.jobs.find_by_key(property_.id, idempotency_key)
            if existing is not None:
                if (existing.recipe_id, existing.batches) != (recipe_id, batches):
                    raise GameRuleError("Esta chave já foi usada em outra operação.")
                state = await self._build_state(user, property_)
                state.replayed = True
                return state

        levels = await self.buildings.levels_by_property(property_.id)
        station = BUILDINGS[recipe.station]
        slots = self._job_slots(station, levels)
        if slots == 0:
            raise GameRuleError(f"Construa «{station.name}» para produzir isto.")
        player_level = (await self.progress.describe(user.id)).level
        if player_level < recipe.min_player_level:
            raise GameRuleError(f"Requer nível de jogador {recipe.min_player_level}.")
        open_jobs = await self.jobs.list_open(property_.id)
        used = sum(1 for job in open_jobs if job.building_id == recipe.station)
        if used >= slots:
            raise GameRuleError(f"{station.name} sem vagas ({used}/{slots}). Colete os prontos.")

        for item_id, per_batch in recipe.inputs.items():
            await self.inventory.consume(
                property_.id, item_id, per_batch * batches, label=_item_name(item_id).lower()
            )

        modifiers = await self.modifiers.for_property(user.id, property_.id)
        job_id = uuid.uuid4()
        rng = seeded_rng("craft", job_id)
        output = scale(
            recipe.output_quantity * batches, modifiers.total_bp(Stat.PRODUCTION_YIELD), rng
        )
        seconds = scaled_seconds(
            recipe.duration_seconds * batches,
            modifiers.total_bp(Stat.PRODUCTION_TIME, recipe.station),
        )
        now = utcnow()
        await self.jobs.add(
            ProductionJob(
                id=job_id,
                property_id=property_.id,
                recipe_id=recipe.id,
                building_id=recipe.station,
                batches=batches,
                output_item=recipe.output_item,
                output_quantity=output,
                started_at=now,
                finish_at=now + timedelta(seconds=seconds),
                request_key=idempotency_key,
            )
        )
        return await self._build_state(user, property_)

    # --------------------------------------------------------------- coleta
    async def collect(self, user: User, property_id: uuid.UUID) -> CraftingState:
        property_ = await self.properties.get_owned(property_id, user.id)
        await self.jobs.lock_property(property_.id)

        now = utcnow()
        ready = [
            job
            for job in await self.jobs.list_open(property_.id)
            if ensure_utc(job.finish_at) <= now
        ]
        if not ready:
            raise GameRuleError("Nenhum trabalho pronto para coletar.")

        collected: dict[str, int] = {}
        base_xp = 0
        for job in ready:
            collected[job.output_item] = collected.get(job.output_item, 0) + job.output_quantity
            recipe = get_recipe(job.recipe_id)
            base_xp += (recipe.xp if recipe else 0) * job.batches
            job.collected_at = now

        for item_id, quantity in collected.items():
            await self.inventory.add(property_.id, item_id, quantity)

        modifiers = await self.modifiers.for_property(user.id, property_.id)
        xp = scale(base_xp, modifiers.total_bp(Stat.XP_GAIN), seeded_rng("craft-xp", ready[0].id))
        grant = await self.progress.grant(user.id, xp)
        await self.jobs.session.flush()

        state = await self._build_state(user, property_)
        state.collected = collected
        state.xp_gained = grant.gained
        return state

    # ------------------------------------------------------------ internos
    @staticmethod
    def _job_slots(station: BuildingDefinition, levels: dict[str, int]) -> int:
        info = station.level_info(levels.get(station.id, station.initial_level))
        return info.job_slots or 0 if info else 0

    async def _build_state(self, user: User, property_: Property) -> CraftingState:
        now = utcnow()
        levels = await self.buildings.levels_by_property(property_.id)
        player_level = (await self.progress.describe(user.id)).level
        open_jobs = list(await self.jobs.list_open(property_.id))
        modifiers = await self.modifiers.for_property(user.id, property_.id)
        stock = {
            row.item_id: row.quantity
            for row in await self.inventory_repo.list_by_property(property_.id)
        }

        stations: list[StationView] = []
        slots_by_station: dict[str, int] = {}
        used_by_station: dict[str, int] = {}
        for station_id in sorted({recipe.station for recipe in RECIPES.values()}):
            definition = get_building(station_id)
            if definition is None:
                continue
            level = levels.get(station_id, definition.initial_level)
            slots = self._job_slots(definition, levels)
            jobs = [job for job in open_jobs if job.building_id == station_id]
            views = []
            for job in jobs:
                recipe = get_recipe(job.recipe_id)
                left = max(0, int((ensure_utc(job.finish_at) - now).total_seconds()))
                views.append(
                    JobView(
                        job,
                        recipe,
                        _item_name(job.output_item),
                        left,
                        ensure_utc(job.finish_at) <= now,
                    )
                )
            slots_by_station[station_id] = slots
            used_by_station[station_id] = len(jobs)
            stations.append(
                StationView(
                    definition=definition,
                    level=level,
                    job_slots=slots,
                    used_slots=len(jobs),
                    time_bonus_bp=modifiers.total_bp(Stat.PRODUCTION_TIME, station_id),
                    jobs=views,
                )
            )

        recipes: list[RecipeView] = []
        for recipe in RECIPES.values():
            inputs = [
                InputView(item_id, _item_name(item_id), per_batch, stock.get(item_id, 0))
                for item_id, per_batch in recipe.inputs.items()
            ]
            affordable = min(view.have // view.per_batch for view in inputs)
            station = BUILDINGS[recipe.station]
            reason: str | None = None
            if slots_by_station.get(recipe.station, 0) == 0:
                reason = f"Construa «{station.name}»."
            elif player_level < recipe.min_player_level:
                reason = f"Requer nível de jogador {recipe.min_player_level}."
            elif used_by_station.get(recipe.station, 0) >= slots_by_station[recipe.station]:
                reason = "Sem vagas na estação. Colete os trabalhos prontos."
            elif affordable == 0:
                reason = "Faltam insumos."
            recipes.append(
                RecipeView(
                    recipe=recipe,
                    output_name=_item_name(recipe.output_item),
                    inputs=inputs,
                    max_batches=min(MAX_BATCHES, affordable) if reason is None else 0,
                    can_craft=reason is None,
                    blocked_reason=reason,
                )
            )

        return CraftingState(
            property=property_, player_level=player_level, stations=stations, recipes=recipes
        )
