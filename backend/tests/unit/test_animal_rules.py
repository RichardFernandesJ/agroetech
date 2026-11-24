"""Regras puras de alimentação e produção dos animais."""

from datetime import UTC, datetime, timedelta

import pytest

from app.game.animals import ANIMALS, advance, feed

T0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
PRODUCE = 900  # galinha
MAX_STORED = 32


def _advance(*, now, last=T0, fed_until=None, progress=0.0, stored=0):
    return advance(
        now=now,
        last_sync_at=last,
        fed_until=fed_until,
        progress_seconds=progress,
        stored=stored,
        produce_seconds=PRODUCE,
        max_stored=MAX_STORED,
    )


def test_catalog_is_consistent() -> None:
    from app.game.buildings import BUILDINGS
    from app.game.catalog import ITEM_CATALOG, get_item

    for animal in ANIMALS.values():
        assert animal.housing in BUILDINGS
        assert animal.product_item in ITEM_CATALOG
        assert get_item(animal.feed_item) is not None
        assert animal.max_stored * animal.produce_seconds >= animal.max_feed_seconds


def test_never_fed_animal_produces_nothing() -> None:
    result = _advance(now=T0 + timedelta(hours=10), fed_until=None)
    assert (result.stored, result.produced, result.lost) == (0, 0, 0)


def test_production_only_counts_while_fed() -> None:
    # Alimentada por 1 hora; passam 10 horas. Só a 1ª hora produz: 4 ovos.
    result = _advance(now=T0 + timedelta(hours=10), fed_until=T0 + timedelta(hours=1))
    assert result.produced == 4 and result.stored == 4


def test_partial_progress_is_carried_over() -> None:
    first = _advance(now=T0 + timedelta(seconds=600), fed_until=T0 + timedelta(hours=8))
    assert (first.produced, first.progress_seconds) == (0, 600)
    second = _advance(
        now=T0 + timedelta(seconds=1000),
        last=T0 + timedelta(seconds=600),
        fed_until=T0 + timedelta(hours=8),
        progress=first.progress_seconds,
    )
    assert second.produced == 1 and second.progress_seconds == pytest.approx(100)


def test_many_small_syncs_equal_one_big_sync() -> None:
    """Sincronizar a cada poucos segundos não perde nem cria produção."""
    fed = T0 + timedelta(hours=8)
    big = _advance(now=T0 + timedelta(hours=3), fed_until=fed)

    progress, stored, last = 0.0, 0, T0
    for step in range(1, 10_801, 7):  # a cada 7 s, durante 3 h
        now = T0 + timedelta(seconds=step)
        part = _advance(now=now, last=last, fed_until=fed, progress=progress, stored=stored)
        progress, stored, last = part.progress_seconds, part.stored, now
    final = _advance(
        now=T0 + timedelta(hours=3), last=last, fed_until=fed, progress=progress, stored=stored
    )
    assert final.stored == big.stored == 12


def test_storage_cap_discards_overflow() -> None:
    result = _advance(now=T0 + timedelta(hours=100), fed_until=T0 + timedelta(hours=100), stored=30)
    assert result.stored == MAX_STORED
    assert result.produced == 2 and result.lost > 0


def test_same_inputs_always_give_same_output() -> None:
    kwargs = dict(now=T0 + timedelta(hours=5), fed_until=T0 + timedelta(hours=4))
    assert _advance(**kwargs) == _advance(**kwargs)


def test_feeding_extends_from_now_when_hungry_and_from_fed_until_when_fed() -> None:
    hungry = feed(now=T0, fed_until=None, units=2, feed_seconds=1800, max_feed_seconds=28_800)
    assert hungry.units_used == 2 and hungry.fed_until == T0 + timedelta(hours=1)

    expired = feed(
        now=T0,
        fed_until=T0 - timedelta(hours=3),
        units=1,
        feed_seconds=1800,
        max_feed_seconds=28_800,
    )
    assert expired.fed_until == T0 + timedelta(minutes=30)

    topup = feed(
        now=T0,
        fed_until=T0 + timedelta(hours=1),
        units=1,
        feed_seconds=1800,
        max_feed_seconds=28_800,
    )
    assert topup.fed_until == T0 + timedelta(minutes=90)


def test_feeding_is_capped_at_the_buffer() -> None:
    result = feed(now=T0, fed_until=None, units=100, feed_seconds=1800, max_feed_seconds=28_800)
    assert result.units_used == 16 and result.fed_until == T0 + timedelta(hours=8)

    full = feed(
        now=T0,
        fed_until=T0 + timedelta(hours=8),
        units=5,
        feed_seconds=1800,
        max_feed_seconds=28_800,
    )
    assert full.units_used == 0 and full.fed_until == T0 + timedelta(hours=8)


def test_animal_economy_is_a_value_add_with_reasonable_payback() -> None:
    """Criar animal compensa (ração vira produto de mais valor), sem ser dinheiro fácil."""
    from app.game.catalog import CROPS

    feed_value = {crop.product_item: crop.sell_price for crop in CROPS.values()}
    for animal in ANIMALS.values():
        products_per_feed = animal.feed_seconds / animal.produce_seconds
        revenue = products_per_feed * animal.sell_price
        cost = feed_value[animal.feed_item]
        assert 1.2 <= revenue / cost <= 3.0, (animal.id, revenue / cost)

        net_per_hour = (revenue - cost) * 3600 / animal.feed_seconds
        payback_hours = animal.price / net_per_hour
        assert 5 <= payback_hours <= 50, (animal.id, payback_hours)
