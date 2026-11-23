"""Produção offline.

A produção é "preguiçosa": não existe job em background. Sempre que a fazenda é
sincronizada (login, abertura da fazenda, plantio, colheita), o servidor simula
o tempo decorrido e armazena as colheitas que amadureceram dentro da janela
offline permitida.

Vantagens:
- funciona igual com o jogador online ou offline;
- não depende de cron/worker;
- é determinística e fácil de testar.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.time import ensure_utc, utcnow
from app.game.catalog import get_crop
from app.game.rules import simulate_growth
from app.game.status import PlantingStatus
from app.models.property import Property
from app.repositories.planting_repository import PlantingRepository


@dataclass(frozen=True, slots=True)
class OfflineSyncReport:
    property_id: uuid.UUID
    synced_at: datetime
    window_start: datetime
    offline_seconds: int
    plantings_synced: int
    cycles_stored: int
    ready_plantings: int


class ProductionService:
    def __init__(
        self,
        session: AsyncSession,
        plantings: PlantingRepository,
    ) -> None:
        self.session = session
        self.plantings = plantings

    async def sync_property(
        self,
        property_: Property,
        now: datetime | None = None,
    ) -> OfflineSyncReport:
        now = ensure_utc(now) if now is not None else utcnow()
        last_sync = ensure_utc(property_.last_production_sync_at)

        # Só simulamos, no máximo, as últimas N horas. O tempo além disso é
        # perdido de propósito (teto de produção offline).
        window_start = max(last_sync, now - timedelta(hours=settings.offline_max_hours))
        if window_start > now:
            window_start = now

        active_plantings = await self.plantings.list_active_by_property(property_.id)

        cycles_stored = 0
        ready_plantings = 0

        for planting in active_plantings:
            crop = get_crop(planting.crop_id)
            if crop is None:
                # Cultura removida do catálogo: ignora o plantio antigo.
                continue

            simulation = simulate_growth(
                next_ready_at=planting.next_ready_at,
                cycles_done=planting.cycles_done,
                stored_cycles=planting.stored_cycles,
                crop=crop,
                now=now,
                window_start=window_start,
                max_stored_cycles=settings.offline_max_cycles_per_planting,
            )

            if simulation.newly_stored_cycles:
                planting.stored_cycles += simulation.newly_stored_cycles
                cycles_stored += simulation.newly_stored_cycles

            planting.next_ready_at = simulation.next_ready_at
            planting.status = simulation.status.value

            if simulation.status is PlantingStatus.READY:
                ready_plantings += 1

        property_.last_production_sync_at = now
        await self.session.flush()

        return OfflineSyncReport(
            property_id=property_.id,
            synced_at=now,
            window_start=window_start,
            offline_seconds=max(0, int((now - last_sync).total_seconds())),
            plantings_synced=len(active_plantings),
            cycles_stored=cycles_stored,
            ready_plantings=ready_plantings,
        )
