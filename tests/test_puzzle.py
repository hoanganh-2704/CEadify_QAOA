"""Tests for src/puzzle.py: brute force, 2-factors, the starter cost, the cost table and baselines."""
import itertools
import time

import numpy as np
import pytest

from src.puzzle import (BONUS, CHOICES, CUBES, all_solutions, baseline, brute_force_towers,
                        cost, cost_table, count_answers, degrees, front_back, instance,
                        is_two_factor, make_puzzle, one_hot, orientations, solves, tower_from,
                        verify_choice)


def test_24_orientations():
    assert len(orientations(CUBES[0])) == 24
    assert len(set(orientations(["AB", "CD", "EF"]))) == 24


def test_brute_force_finds_8_towers_fast():
    start = time.perf_counter()
    winners = brute_force_towers(CUBES)
    assert time.perf_counter() - start < 3
    assert len(winners) == 8
    assert all(solves(t) for t in winners)
    assert 24 ** 4 == 331_776


def test_brute_force_refuses_large_n():
    with pytest.raises(ValueError):
        brute_force_towers(instance(6))


def test_front_back_picks():
    assert front_back == [(0, 2, 2, 2), (1, 0, 2, 2), (2, 1, 2, 2), (2, 2, 0, 1)]
    assert all(is_two_factor(CUBES, picks) for picks in front_back)


def test_starter_cost_has_two_zeros_over_one_hot_candidates():
    scores = np.array([cost(CUBES, [one_hot(p) for p in fb], [one_hot(p) for p in lr])
                       for fb in itertools.product(range(3), repeat=4)
                       for lr in itertools.product(range(3), repeat=4)])
    assert len(scores) == 6561
    assert (scores == 0).sum() == 2
    assert np.unique(scores)[1] == 2


def test_all_solutions_are_verified():
    sols = all_solutions(CUBES)
    assert len(sols) == 2 == count_answers(CUBES)
    assert all(verify_choice(CUBES, s) for s in sols)


def _symmetries(tower):
    """The 8 towers you get by turning the whole (front, right, back, left) tower or swapping front/back."""
    out = set()
    for turn in range(4):
        rotated = tuple(tuple(v[(i + turn) % 4] for i in range(4)) for v in tower)
        out.add(rotated)
        out.add(tuple((v[2], v[1], v[0], v[3]) for v in rotated))
    return out


def test_brute_force_matches_graph_answers():
    brute = {tuple((v[0], v[3], v[1], v[2]) for v in t) for t in brute_force_towers(CUBES)}
    from_graph = set()
    for s in all_solutions(CUBES):
        from_graph |= _symmetries(tuple(tower_from(CUBES, s)))
    assert brute == from_graph


@pytest.mark.parametrize("n", [3, 4, 5, 6, pytest.param(7, marks=pytest.mark.slow),
                               pytest.param(8, marks=pytest.mark.slow)])
def test_cost_table_zeros_match_count_answers(n):
    cubes = instance(n)
    table = cost_table(cubes)
    assert table.shape == (6 ** n,)
    assert (table == 0).sum() == count_answers(cubes) == 2
    assert np.unique(table)[1] == 2
    assert np.all(table % 2 == 0)


def test_cost_table_matches_starter_cost():
    table = cost_table(CUBES)
    rng = np.random.default_rng(7)
    for index in rng.integers(0, 6 ** 4, 50):
        choice = [CHOICES[(index // 6 ** c) % 6] for c in range(4)]
        x = [one_hot(fb) for fb, _ in choice]
        y = [one_hot(lr) for _, lr in choice]
        assert cost(CUBES, x, y) == table[index]


def test_colour_safety_on_bonus_letters():
    cubes = make_puzzle(5, 16)
    choice = all_solutions(cubes)[0]
    x = [one_hot(fb) for fb, _ in choice]
    y = [one_hot(lr) for _, lr in choice]
    assert cost(cubes, x, y) == 0
    assert cost(cubes, x, y, colours="RGBY") != 0
    picks = [fb for fb, _ in choice]
    assert set(degrees(cubes, picks).values()) == {2}
    assert degrees(cubes, picks) != degrees(cubes, picks, colours="RGBY")


@pytest.mark.parametrize("n", [5, 6, pytest.param(7, marks=pytest.mark.slow),
                               pytest.param(8, marks=pytest.mark.slow)])
def test_bonus_seeds_have_one_tower(n):
    assert count_answers(make_puzzle(n, BONUS[n])) == 2


def test_instance_n3_has_one_tower():
    assert count_answers(instance(3)) == 2


@pytest.mark.parametrize("kind, value", [("bits6N", 1.192e-7), ("bits3N", 4.883e-4),
                                         ("valid6N", 1.543e-3), ("WxW", 3.048e-4),
                                         ("fb_bits", 4 / 4096), ("fb_valid", 4 / 81)])
def test_baselines(kind, value):
    assert baseline(4, kind) == pytest.approx(value, rel=1e-3 if kind not in ("fb_bits", "fb_valid") else 1e-6)
