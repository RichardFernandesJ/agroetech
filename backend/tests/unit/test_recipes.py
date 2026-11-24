"""Consistência do catálogo de receitas e da economia de fabricação."""

from app.game.animals import ANIMALS
from app.game.buildings import BUILDINGS
from app.game.catalog import CROPS, ITEM_CATALOG
from app.game.economy import product_prices
from app.game.recipes import MAX_BATCHES, PROCESSED_ITEMS, RECIPES


def _producible_items() -> set[str]:
    items = {crop.product_item for crop in CROPS.values()}
    items |= {animal.product_item for animal in ANIMALS.values()}
    items |= {recipe.output_item for recipe in RECIPES.values()}
    return items


def test_every_recipe_is_consistent() -> None:
    producible = _producible_items()
    for recipe in RECIPES.values():
        station = BUILDINGS[recipe.station]
        assert station.levels[0].job_slots, "a estação precisa de vagas de produção"
        assert recipe.min_player_level >= station.levels[0].min_player_level, recipe.id
        assert recipe.output_item in ITEM_CATALOG and recipe.output_item in product_prices()
        for item_id, quantity in recipe.inputs.items():
            assert item_id in ITEM_CATALOG, (recipe.id, item_id)
            assert item_id in producible, f"{recipe.id}: ninguém produz {item_id}"
            assert quantity >= 1
        assert recipe.duration_seconds > 0 and recipe.output_quantity >= 1 and recipe.xp > 0


def test_processed_items_are_sellable_and_unique() -> None:
    assert {recipe.output_item for recipe in RECIPES.values()} <= set(PROCESSED_ITEMS)
    prices = product_prices()
    assert all(prices[item_id] == item.sell_price for item_id, item in PROCESSED_ITEMS.items())


def test_recipes_do_not_loop_into_themselves() -> None:
    for recipe in RECIPES.values():
        assert recipe.output_item not in recipe.inputs


def test_processing_adds_value_without_free_money() -> None:
    """Produzir vale a pena (ganho entre 15% e 100% sobre os insumos), sem ser dinheiro fácil."""
    prices = product_prices()
    for recipe in RECIPES.values():
        cost = sum(prices[item] * quantity for item, quantity in recipe.inputs.items())
        revenue = prices[recipe.output_item] * recipe.output_quantity
        assert 1.15 <= revenue / cost <= 2.0, (recipe.id, revenue / cost)


def test_batch_limit_is_sane() -> None:
    assert 1 < MAX_BATCHES <= 100
