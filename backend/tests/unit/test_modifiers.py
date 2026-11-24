"""Motor de modificadores: soma, escopo, tetos e determinismo."""

from app.game.modifiers import (
    BP,
    STAT_LIMITS,
    Effect,
    ModifierSet,
    Stat,
    effective_fee_bp,
    roll,
    scale,
    scaled_seconds,
    seeded_rng,
)


def test_empty_set_has_no_bonus() -> None:
    mods = ModifierSet()
    assert all(value == 0 for value in mods.snapshot().values())


def test_global_and_scoped_effects_add_up_for_the_scope_only() -> None:
    mods = ModifierSet(
        [
            Effect(Stat.CROP_YIELD, 200),
            Effect(Stat.CROP_YIELD, 600, "milho"),
        ]
    )
    assert mods.total_bp(Stat.CROP_YIELD, "milho") == 800
    assert mods.total_bp(Stat.CROP_YIELD, "tomate") == 200
    assert mods.total_bp(Stat.CROP_YIELD) == 200


def test_totals_are_clamped_to_caps() -> None:
    mods = ModifierSet(
        [
            Effect(Stat.CROP_YIELD, 10_000),
            Effect(Stat.CROP_GROW_TIME, -9_000),
            Effect(Stat.MARKET_FEE, -5_000),
        ]
    )
    assert mods.total_bp(Stat.CROP_YIELD) == STAT_LIMITS[Stat.CROP_YIELD][1]
    assert mods.total_bp(Stat.CROP_GROW_TIME) == STAT_LIMITS[Stat.CROP_GROW_TIME][0]
    assert mods.total_bp(Stat.MARKET_FEE) == STAT_LIMITS[Stat.MARKET_FEE][0]


def test_caps_keep_grow_time_positive_and_fee_above_minimum() -> None:
    assert scaled_seconds(300, STAT_LIMITS[Stat.CROP_GROW_TIME][0]) > 0
    assert scaled_seconds(1, -9_999) == 1
    assert effective_fee_bp(500, -9_000) == 100


def test_seeded_rng_is_deterministic() -> None:
    first = [seeded_rng("harvest", "abc", 3).random() for _ in range(3)]
    second = [seeded_rng("harvest", "abc", 3).random() for _ in range(3)]
    other = seeded_rng("harvest", "abc", 4).random()
    assert first == second
    assert other != first[0]


def test_scale_keeps_integer_part_and_averages_to_exact_value() -> None:
    # 3 unidades com +50% = 4,5 esperado: resultado é 4 ou 5, nunca outro valor.
    results = [scale(3, 5_000, seeded_rng("t", n)) for n in range(2_000)]
    assert set(results) == {4, 5}
    assert abs(sum(results) / len(results) - 4.5) < 0.1
    # Sem bônus não há sorteio: o valor é exato.
    assert scale(7, 0, seeded_rng("x")) == 7


def test_roll_respects_extremes() -> None:
    assert not roll(0, seeded_rng("a"))
    assert all(roll(BP + 1, seeded_rng("a", n)) for n in range(20))


def test_free_batches_extremes_and_distribution() -> None:
    from app.game.modifiers import free_batches

    assert free_batches(10, 0, seeded_rng("a")) == 0
    assert free_batches(10, BP + 1, seeded_rng("a")) == 10
    total = sum(free_batches(10, 2_000, seeded_rng("lote", n)) for n in range(1_000))
    assert abs(total / 1_000 - 2.0) < 0.2  # 20% de 10 lotes
    assert free_batches(24, 1_500, seeded_rng("x")) == free_batches(24, 1_500, seeded_rng("x"))
