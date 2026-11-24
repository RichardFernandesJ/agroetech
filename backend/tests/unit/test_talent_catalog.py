"""Consistência do catálogo de talentos e paridade entre builds."""

import pytest

from app.core.exceptions import AppError
from app.game.talents import BRANCHES, NODES, NODES_BY_ID, TIERS, validate_catalog
from app.services.talent_service import check_allocatable, points_total, spent_points
from tests.unit.balance import BUILDS, DOMAIN_BUILDS, best_profit_per_hour, xp_per_hour

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
    assert available == {"agricultura", "comercio", "pecuaria", "industria"}
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


def _domain_gain(node_ids: list[str], domain: str) -> float:
    from tests.unit.balance import (
        best_animal_profit_per_hour,
        best_craft_profit_per_hour,
        best_profit_per_hour,
    )

    best = {
        "crops": best_profit_per_hour,
        "animals": best_animal_profit_per_hour,
        "crafting": best_craft_profit_per_hour,
    }[domain]
    return best(node_ids) / best([])


@pytest.mark.parametrize(
    "name", sorted(__import__("tests.unit.balance", fromlist=["x"]).DOMAIN_BUILDS)
)
def test_domain_builds_are_valid_and_fit_the_budget(name: str) -> None:
    from tests.unit.balance import DOMAIN_BUILDS

    assert spent_points(_build(DOMAIN_BUILDS[name])) <= MAX_LEVEL_POINTS


def test_each_specialist_wins_its_own_domain_without_being_overpowered() -> None:
    """Paridade entre especialistas, e ninguém vence o especialista no domínio dele.

    Domínios de margem fina (animais e fabricação) amplificam bônus percentuais; por
    isso o simulador compara cada especialista com o melhor "intruso" no mesmo domínio.
    """
    specialists = {
        "crops": ("agricultor", BUILDS["agricultor"]),
        "animals": ("pecuarista", DOMAIN_BUILDS["pecuarista"]),
        "crafting": ("industrial", DOMAIN_BUILDS["industrial"]),
    }
    gains = {}
    for domain, (name, nodes) in specialists.items():
        gains[name] = _domain_gain(nodes, domain)
        assert 1.8 <= gains[name] <= 2.4, (name, gains[name])

        rivals = [
            _domain_gain(other_nodes, domain)
            for other_name, other_nodes in {**BUILDS, **DOMAIN_BUILDS}.items()
            if other_name != name
        ]
        assert gains[name] >= max(rivals) * 1.05, (domain, gains[name], max(rivals))

    assert max(gains.values()) / min(gains.values()) <= 1.2, gains
