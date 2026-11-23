"""Testes unitários das regras puras de crescimento (sem banco/HTTP)."""

from datetime import UTC, datetime, timedelta

from app.game.catalog import CROPS
from app.game.rules import simulate_growth
from app.game.status import PlantingStatus

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=UTC)


def test_crop_still_growing() -> None:
    result = simulate_growth(
        next_ready_at=NOW + timedelta(minutes=5),
        cycles_done=0,
        stored_cycles=0,
        crop=CROPS["tomate"],
        now=NOW,
        window_start=NOW - timedelta(hours=1),
        max_stored_cycles=8,
    )

    assert result.newly_stored_cycles == 0
    assert result.status is PlantingStatus.GROWING


def test_single_completed_cycle_becomes_ready() -> None:
    next_ready = NOW - timedelta(seconds=1)
    result = simulate_growth(
        next_ready_at=next_ready,
        cycles_done=0,
        stored_cycles=0,
        crop=CROPS["tomate"],
        now=NOW,
        window_start=NOW - timedelta(hours=1),
        max_stored_cycles=8,
    )

    assert result.newly_stored_cycles == 1
    assert result.status is PlantingStatus.READY
    assert result.next_ready_at == next_ready + timedelta(seconds=CROPS["tomate"].grow_seconds)


def test_cycles_before_offline_window_are_discarded() -> None:
    # Café cresce de 1h em 1h. O primeiro ciclo maduro foi há 3h; a janela
    # começa há 1h, então 2 ciclos antigos são perdidos e 2 são armazenados.
    result = simulate_growth(
        next_ready_at=NOW - timedelta(hours=3),
        cycles_done=0,
        stored_cycles=0,
        crop=CROPS["cafe"],
        now=NOW,
        window_start=NOW - timedelta(hours=1),
        max_stored_cycles=8,
    )

    assert result.expired_cycles == 2
    assert result.newly_stored_cycles == 2
    assert result.status is PlantingStatus.READY


def test_stored_cycles_cap_limits_production() -> None:
    result = simulate_growth(
        next_ready_at=NOW - timedelta(hours=20),
        cycles_done=0,
        stored_cycles=0,
        crop=CROPS["cafe"],
        now=NOW,
        window_start=NOW - timedelta(hours=12),
        max_stored_cycles=2,
    )

    assert result.newly_stored_cycles == 2
    assert result.overflow_cycles > 0


def test_exhausted_crop_does_not_produce() -> None:
    crop = CROPS["tomate"]
    result = simulate_growth(
        next_ready_at=NOW - timedelta(days=1),
        cycles_done=crop.max_cycles,
        stored_cycles=0,
        crop=crop,
        now=NOW,
        window_start=NOW - timedelta(hours=12),
        max_stored_cycles=8,
    )

    assert result.newly_stored_cycles == 0
    assert result.status is PlantingStatus.EXHAUSTED


def test_max_cycles_caps_stored_cycles() -> None:
    crop = CROPS["tomate"]
    result = simulate_growth(
        next_ready_at=NOW - timedelta(hours=5),
        cycles_done=0,
        stored_cycles=0,
        crop=crop,
        now=NOW,
        window_start=NOW - timedelta(hours=12),
        max_stored_cycles=8,
    )

    assert result.newly_stored_cycles == crop.max_cycles
    assert result.status is PlantingStatus.READY
