"""Regras puras de crescimento e produção offline.

Este módulo não conhece banco nem HTTP, o que o torna fácil de testar: dado um
plantio e um instante, calcula quantos ciclos amadureceram, quantos foram
perdidos e qual deve ser o próximo horário de colheita.

Regras:
- Cada ciclo concluído fica "armazenado" no plantio, pronto para colheita.
- Apenas ciclos concluídos dentro da janela offline (últimas N horas) são
  armazenados; os anteriores são perdidos.
- O plantio também tem um teto de ciclos armazenados por sincronização.
- ``max_cycles`` limita o total de colheitas da cultura (ex.: tomate = 3).
"""

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.time import ensure_utc
from app.game.catalog import CropDefinition
from app.game.status import PlantingStatus


@dataclass(frozen=True, slots=True)
class GrowthSimulation:
    newly_stored_cycles: int
    expired_cycles: int
    overflow_cycles: int
    next_ready_at: datetime
    status: PlantingStatus


def simulate_growth(
    *,
    next_ready_at: datetime,
    cycles_done: int,
    stored_cycles: int,
    crop: CropDefinition,
    now: datetime,
    window_start: datetime,
    max_stored_cycles: int,
) -> GrowthSimulation:
    next_ready_at = ensure_utc(next_ready_at)
    now = ensure_utc(now)
    window_start = ensure_utc(window_start)

    remaining_cycles = crop.max_cycles - cycles_done - stored_cycles
    if remaining_cycles <= 0:
        status = PlantingStatus.READY if stored_cycles > 0 else PlantingStatus.EXHAUSTED
        return GrowthSimulation(0, 0, 0, next_ready_at, status)

    if now < next_ready_at:
        status = PlantingStatus.READY if stored_cycles > 0 else PlantingStatus.GROWING
        return GrowthSimulation(0, 0, 0, next_ready_at, status)

    interval = timedelta(seconds=crop.grow_seconds)
    completed = int((now - next_ready_at) / interval) + 1

    # Ciclos que amadureceram antes do início da janela offline são perdidos.
    if window_start <= next_ready_at:
        expired = 0
    else:
        expired = min(completed, math.ceil((window_start - next_ready_at) / interval))
    in_window = completed - expired

    capacity = min(remaining_cycles, max(0, max_stored_cycles - stored_cycles))
    newly_stored = min(in_window, capacity)
    overflow = in_window - newly_stored

    total_stored = stored_cycles + newly_stored
    if total_stored > 0:
        status = PlantingStatus.READY
    elif cycles_done + total_stored >= crop.max_cycles:
        status = PlantingStatus.EXHAUSTED
    else:
        status = PlantingStatus.GROWING

    return GrowthSimulation(
        newly_stored_cycles=newly_stored,
        expired_cycles=expired,
        overflow_cycles=overflow,
        next_ready_at=next_ready_at + completed * interval,
        status=status,
    )
