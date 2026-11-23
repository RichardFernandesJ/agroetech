"""Regras da árvore de talentos: pontos, alocação, presets e redefinição.

Tudo é validado aqui; o cliente só informa a intenção (``node_id``). Os bônus
resultantes saem de :meth:`TalentService.modifiers_for` e são aplicados pelas
mecânicas através do motor central (``game/modifiers.py``).
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.core.time import ensure_utc, utcnow
from app.game.modifiers import Effect, ModifierSet
from app.game.talents import NODES_BY_ID, TalentNode, get_branch, get_node
from app.models.talent import TalentPreset, TalentRespec
from app.repositories.talent_repository import TalentRepository
from app.services.progress_service import ProgressService
from app.services.wallet_service import WalletService

MAX_PRESET_SLOTS = 5


def points_total(level: int) -> int:
    """Um ponto de talento por nível a partir do nível 2."""
    return max(0, level - 1)


def preset_slots(level: int) -> int:
    return min(MAX_PRESET_SLOTS, 1 + level // 10)


def spent_points(node_ids: Iterable[str]) -> int:
    return sum(NODES_BY_ID[node_id].cost for node_id in node_ids if node_id in NODES_BY_ID)


def spent_in_branch(node_ids: Iterable[str], branch: str) -> int:
    return sum(
        NODES_BY_ID[node_id].cost
        for node_id in node_ids
        if node_id in NODES_BY_ID and NODES_BY_ID[node_id].branch == branch
    )


def check_allocatable(
    node: TalentNode,
    owned: set[str],
    level: int,
    available_points: int,
) -> None:
    branch = get_branch(node.branch)
    if branch is not None and not branch.available:
        raise GameRuleError("Este ramo ainda não está disponível.")
    if node.id in owned:
        raise ConflictError("Você já possui este talento.")
    if level < node.min_level:
        raise GameRuleError(f"Requer nível {node.min_level}.")
    for required in node.requires:
        if required not in owned:
            raise GameRuleError(f"Requer o talento «{NODES_BY_ID[required].name}».")
    if node.requires_any and not any(ref in owned for ref in node.requires_any):
        names = " ou ".join(f"«{NODES_BY_ID[ref].name}»" for ref in node.requires_any)
        raise GameRuleError(f"Requer um dos talentos: {names}.")
    for branch_id, needed in node.branch_points:
        if spent_in_branch(owned, branch_id) < needed:
            label = get_branch(branch_id)
            name = label.name if label else branch_id
            raise GameRuleError(f"Requer {needed} pontos investidos em {name}.")
    if node.exclusive_group is not None:
        for other in owned:
            if NODES_BY_ID[other].exclusive_group == node.exclusive_group:
                raise ConflictError("Você já escolheu outro talento mestre deste ramo.")
    if node.cost > available_points:
        raise GameRuleError("Pontos de talento insuficientes.")


@dataclass(frozen=True, slots=True)
class PresetView:
    preset: TalentPreset
    node_ids: tuple[str, ...]
    points_spent: int


@dataclass(frozen=True, slots=True)
class TalentState:
    level: int
    points_total: int
    points_spent: int
    points_available: int
    preset_slots: int
    presets: tuple[PresetView, ...]
    switch_available_at: datetime | None
    reset_cost: int
    reset_is_free: bool
    build_locked: bool
    modifiers: dict[str, int]


class TalentService:
    def __init__(
        self,
        talents: TalentRepository,
        progress: ProgressService,
        wallets: WalletService,
    ) -> None:
        self.talents = talents
        self.progress = progress
        self.wallets = wallets

    # ------------------------------------------------------------ consultas
    async def modifiers_for(self, user_id: uuid.UUID) -> ModifierSet:
        """Modificadores do preset ativo (vazio se o jogador ainda não tem talentos)."""
        active = await self.talents.get_active(user_id)
        if active is None:
            return ModifierSet()
        effects: list[Effect] = []
        for node in active.nodes:
            definition = get_node(node.node_id)
            if definition is not None:
                effects.extend(definition.effects)
        return ModifierSet(effects)

    async def is_build_locked(self, user_id: uuid.UUID) -> bool:
        """Ponto de extensão: disputas ativas congelarão a build (Fases 6 e 7)."""
        return False

    async def state(self, user_id: uuid.UUID) -> TalentState:
        level = (await self.progress.describe(user_id)).level
        await self._ensure_preset(user_id)
        presets = await self.talents.list_presets(user_id)
        views = tuple(self._view(preset) for preset in presets)
        active = next((view for view in views if view.preset.is_active), None)
        spent = active.points_spent if active else 0
        free = await self.talents.count_respecs(user_id) == 0
        return TalentState(
            level=level,
            points_total=points_total(level),
            points_spent=spent,
            points_available=max(0, points_total(level) - spent),
            preset_slots=preset_slots(level),
            presets=views,
            switch_available_at=self._switch_available_at(presets),
            reset_cost=0 if free else level * settings.talent_reset_cost_per_level,
            reset_is_free=free,
            build_locked=await self.is_build_locked(user_id),
            modifiers=(await self.modifiers_for(user_id)).snapshot(),
        )

    # ------------------------------------------------------------- alocação
    async def allocate(self, user_id: uuid.UUID, node_id: str) -> None:
        await self._ensure_not_locked(user_id)
        node = get_node(node_id)
        if node is None:
            raise NotFoundError("Talento não encontrado.")

        level = (await self.progress.describe(user_id)).level
        await self._ensure_preset(user_id)
        active = await self.talents.get_active(user_id, for_update=True)
        assert active is not None
        owned = {entry.node_id for entry in active.nodes}

        available = points_total(level) - spent_points(owned)
        check_allocatable(node, owned, level, available)
        await self.talents.add_node(active.id, node.id)

    # -------------------------------------------------------------- presets
    async def create_preset(self, user_id: uuid.UUID, name: str) -> TalentPreset:
        await self._ensure_not_locked(user_id)
        level = (await self.progress.describe(user_id)).level
        await self._ensure_preset(user_id)
        presets = await self.talents.list_presets(user_id)
        if len(presets) >= preset_slots(level):
            raise GameRuleError("Sem espaços livres para novos presets neste nível.")
        used = {preset.slot for preset in presets}
        slot = next(n for n in range(1, MAX_PRESET_SLOTS + 1) if n not in used)
        return await self.talents.add(
            TalentPreset(user_id=user_id, name=self._clean_name(name), slot=slot, is_active=False)
        )

    async def rename_preset(self, user_id: uuid.UUID, preset_id: uuid.UUID, name: str) -> None:
        preset = await self._get_preset(user_id, preset_id)
        preset.name = self._clean_name(name)
        await self.talents.session.flush()

    async def delete_preset(self, user_id: uuid.UUID, preset_id: uuid.UUID) -> None:
        preset = await self._get_preset(user_id, preset_id)
        if preset.is_active:
            raise GameRuleError("Ative outro preset antes de excluir este.")
        await self.talents.delete(preset)

    async def activate_preset(self, user_id: uuid.UUID, preset_id: uuid.UUID) -> None:
        await self._ensure_not_locked(user_id)
        target = await self._get_preset(user_id, preset_id)
        if target.is_active:
            return

        presets = await self.talents.list_presets(user_id)
        available_at = self._switch_available_at(presets)
        now = utcnow()
        if available_at is not None and now < available_at:
            raise GameRuleError("Troca de build em recarga. Tente novamente mais tarde.")

        for preset in presets:
            if preset.is_active:
                preset.is_active = False
        await self.talents.session.flush()
        target.is_active = True
        target.last_activated_at = now
        await self.talents.session.flush()

    # ----------------------------------------------------------- redefinição
    async def reset_active(self, user_id: uuid.UUID) -> int:
        """Remove todos os talentos do preset ativo. Retorna o custo cobrado em AGC."""
        await self._ensure_not_locked(user_id)
        level = (await self.progress.describe(user_id)).level
        await self._ensure_preset(user_id)
        active = await self.talents.get_active(user_id, for_update=True)
        assert active is not None
        if not active.nodes:
            raise GameRuleError("O preset ativo não tem talentos para redefinir.")

        free = await self.talents.count_respecs(user_id) == 0
        cost = 0 if free else level * settings.talent_reset_cost_per_level
        if cost > 0:
            wallet = await self.wallets.get_locked(user_id)
            await self.wallets.apply(wallet, kind="talent_respec", amount=-cost)

        removed = await self.talents.clear_nodes(active.id)
        await self.talents.add_respec(
            TalentRespec(user_id=user_id, preset_id=active.id, nodes_removed=removed, cost=cost)
        )
        return cost

    # ------------------------------------------------------------- internos
    async def _ensure_not_locked(self, user_id: uuid.UUID) -> None:
        if await self.is_build_locked(user_id):
            raise GameRuleError("Sua build está congelada durante uma disputa.")

    async def _ensure_preset(self, user_id: uuid.UUID) -> None:
        if await self.talents.list_presets(user_id):
            return
        await self.talents.add(
            TalentPreset(user_id=user_id, name="Build 1", slot=1, is_active=True)
        )

    async def _get_preset(self, user_id: uuid.UUID, preset_id: uuid.UUID) -> TalentPreset:
        preset = await self.talents.get_preset(user_id, preset_id)
        if preset is None:
            raise NotFoundError("Preset não encontrado.")
        return preset

    @staticmethod
    def _clean_name(name: str) -> str:
        cleaned = " ".join(name.split())
        if not cleaned:
            raise GameRuleError("O nome do preset não pode ficar vazio.")
        return cleaned[:30]

    @staticmethod
    def _view(preset: TalentPreset) -> PresetView:
        node_ids = tuple(sorted(entry.node_id for entry in preset.nodes))
        return PresetView(preset=preset, node_ids=node_ids, points_spent=spent_points(node_ids))

    @staticmethod
    def _switch_available_at(presets: Iterable[TalentPreset]) -> datetime | None:
        stamps = [ensure_utc(p.last_activated_at) for p in presets if p.last_activated_at]
        if not stamps:
            return None
        return max(stamps) + timedelta(seconds=settings.talent_switch_cooldown_seconds)
