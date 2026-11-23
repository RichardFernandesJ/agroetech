"""Consistência do catálogo de talentos e paridade entre builds."""

import pytest

from app.core.exceptions import AppError
from app.game.talents import BRANCHES, NODES, NODES_BY_ID, TIERS, validate_catalog
from app.services.talent_service import check_allocatable, points_total, spent_points
from tests.unit.balance import BUILDS, best_profit_per_hour, xp_per_hour

MAX_LEVEL_POINTS = points_total(50)


def test_catalog_is_consistent() -> None:
    assert validate_catalog() == []


def test_ids_are_unique_and_costs_follow_tiers() -> None:
    assert len(NODES_BY_ID) == len(NODES)
    for node in NODES:
        assert node.cost == TIERS[node.tier][0]
        assert node.effects, node.id


def test_only_branches_with_mechanics_have_talents() -> None:
    available = {branch.id for branch in BRANCHES if branch.available}
    assert available == {"agricultura", "comercio"}
    assert {node.branch for node in NODES} <= available | {"hibrido"}


def test_tree_is_wider_than_the_point_budget() -> None:
    """Ninguém pega tudo: força escolhas (especialização)."""
    assert spent_points(NODES_BY_ID) > MAX_LEVEL_POINTS


def _build(node_ids: list[str]) -> set[str]:
    owned: set[str] = set()
    for node_id in node_ids:
        check_allocatable(NODES_BY_ID[node_id], owned, 50, MAX_LEVEL_POINTS - spent_points(owned))
        owned.add(node_id)
    return owned


@pytest.mark.parametrize("name", sorted(BUILDS))
def test_reference_builds_are_valid_and_fit_the_budget(name: str) -> None:
    owned = _build(BUILDS[name])
    assert spent_points(owned) <= MAX_LEVEL_POINTS


def test_two_masters_of_one_branch_are_exclusive() -> None:
    owned = _build(BUILDS["agricultor"])
    with pytest.raises(AppError):
        check_allocatable(NODES_BY_ID["agro_mestre_tempo"], owned, 50, 49)


def test_legendary_requires_a_master() -> None:
    owned = _build(BUILDS["agricultor"][:10])
    with pytest.raises(AppError):
        check_allocatable(NODES_BY_ID["agro_colheita_dourada"], owned, 50, 49)


def test_builds_stay_within_ten_percent_of_each_other() -> None:
    """Paridade: nenhuma especialização domina em AGC por hora."""
    baseline = best_profit_per_hour([])
    ratios = {name: best_profit_per_hour(nodes) / baseline for name, nodes in BUILDS.items()}

    for name, ratio in ratios.items():
        assert 1.5 <= ratio <= 2.2, (name, ratio)
    assert max(ratios.values()) / min(ratios.values()) <= 1.10, ratios

    xp_ratios = [xp_per_hour(nodes) / xp_per_hour([]) for nodes in BUILDS.values()]
    assert max(xp_ratios) / min(xp_ratios) <= 1.15, xp_ratios
