"""Tests for src/grover.py: the rules-only oracle marks exactly the answers, the K law, and the K = 19 circuit."""
import math

import pytest
from qiskit.quantum_info import Statevector

from src.compact import choice_from_codes, codes_from_key, decode_tower, key_from_codes
from src.grover import (build_oracle, grover_circuit, grover_iterations, grover_success, marked_states,
                        oracle_expression, resource_estimate, valid_prep)
from src.puzzle import ALT4, CHOICES, CUBES, all_solutions, make_puzzle, solves, tower_from, verify_choice
from src.report import compact_valid, success_rate
from src.runtime import aer_counts, circuit_metrics, exact_distribution, prepare_safe


def answer_indices(cubes):
    """Statevector indices of the classical answers (all_solutions) in the compact encoding."""
    return sorted(int(key_from_codes([CHOICES.index(pick) for pick in choice]), 2) for choice in all_solutions(cubes))


def raw_success(cubes, qc):
    """Exact P(correct tower) of a measurement-free 3N-qubit circuit, by Statevector."""
    probs = Statevector(qc).probabilities_dict()
    return sum(p for key, p in probs.items() if decode_tower(cubes, key))


@pytest.fixture(scope="module")
def k19():
    """The K = 19 Grover circuit on CUBES and its prepared (transpiled, 14-qubit) version."""
    core = grover_circuit(CUBES, 19)
    return core, prepare_safe(core)


def test_expression_has_no_answer_knowledge():
    """The formula is built from the cube faces and the rules only: variables x0..x11 and logic symbols."""
    import re
    expr = oracle_expression(CUBES)
    assert set(expr) <= set("x0123456789&|~() ")
    assert {int(v) for v in re.findall(r"x(\d+)", expr)} == set(range(12))
    assert expr.count("&") > 100


@pytest.mark.parametrize("cubes", [CUBES, make_puzzle(4, ALT4)], ids=["CUBES", "make_puzzle(4,57)"])
def test_marked_states_are_the_answers(cubes):
    marked = marked_states(cubes)
    assert sorted(marked) == answer_indices(cubes)
    assert len(marked) == 2
    for idx in marked:
        assert verify_choice(cubes, choice_from_codes(codes_from_key(format(idx, "012b"), 4)))


def test_iteration_formula():
    assert [grover_iterations(n) for n in (4, 5, 6, 7, 8)] == [19, 48, 119, 293, 719]
    assert abs(grover_success(4, 19) - 0.9985) < 1e-4


def test_iteration_count_is_best_of_neighbours():
    """F10 regression: N = 3, M = 2 wants K = 8 (0.9954), not the floored K = 7 (0.9844)."""
    assert grover_iterations(3, 2) == 8
    for n, m in ((3, 2), (3, 12), (4, 2), (5, 2), (2, 1)):
        k = grover_iterations(n, m)
        assert grover_success(n, k, m) >= max(grover_success(n, k - 1, m) if k else 0, grover_success(n, k + 1, m))
    with pytest.raises(ValueError):
        grover_iterations(3, 0)


def test_same_colour_pair_counts_twice():
    """F5 regression: make_puzzle(3, 2) has a "BB" pair; its 12 classical answers must all be marked."""
    cubes = make_puzzle(3, 2)
    assert any(pair[0] == pair[1] for cube in cubes for pair in cube)
    assert len(all_solutions(cubes)) == 12
    assert sorted(marked_states(cubes)) == answer_indices(cubes)


def test_diagonal_fallback_marks_the_same_states(monkeypatch):
    """The Qiskit 1.3 fallback oracle (rule evaluated per code string) marks exactly what the synthesised one marks."""
    import src.grover as G
    expected = sorted(marked_states(CUBES))
    monkeypatch.setattr(G, "ORACLE_BACKEND", "diagonal")
    monkeypatch.setattr(G, "_ORACLES", {})
    assert sorted(marked_states(CUBES)) == expected == answer_indices(CUBES)
    cubes = make_puzzle(3, 2)
    assert sorted(marked_states(cubes)) == answer_indices(cubes)
    k = grover_iterations(3, 12)
    assert abs(raw_success(cubes, grover_circuit(cubes, k)) - grover_success(3, k, 12)) < 1e-9


def test_valid_prep_is_uniform6():
    probs = Statevector(valid_prep(1)).probabilities()
    assert max(abs(probs[k] - 1 / 6) for k in range(6)) < 1e-12 and probs[6] + probs[7] < 1e-12


@pytest.mark.parametrize("k", [1, 3])
def test_small_k_matches_formula(k):
    assert abs(raw_success(CUBES, grover_circuit(CUBES, k)) - grover_success(4, k)) < 1e-9


def test_g1_no_spare_qubit(k19):
    core, _ = k19
    assert core.num_qubits == 12 and core.num_clbits == 0
    assert build_oracle(CUBES).num_qubits == 12


def test_k19_prepared_metrics_and_exact_p(k19):
    _, qc = k19
    m = circuit_metrics(qc)
    assert m["qubits"] == 14
    assert abs(m["cx"] - 3987) <= 0.01 * 3987
    p_exact = success_rate(exact_distribution(qc), lambda key: decode_tower(CUBES, key))["P"]
    assert abs(p_exact - 0.9985) < 1e-4


def test_k19_aer_every_good_shot_verified(k19):
    from src.runtime import strip_marker_safe
    _, qc = k19
    counts = strip_marker_safe(aer_counts(qc, 2000))
    s = success_rate(counts, lambda key: decode_tower(CUBES, key), valid=compact_valid)
    assert s["P"] >= 0.99
    for key in s["objects"]:
        choice = choice_from_codes(codes_from_key(key, 4))
        assert solves(tower_from(CUBES, choice))


def test_resource_estimate_labels():
    rows = resource_estimate()
    assert [r["K"] for r in rows] == [48, 119, 293, 719]
    assert all(r["label"] == "estimate, not run" for r in rows)
    assert all(math.isclose(r["P_theory"], grover_success(r["N"], r["K"])) for r in rows)
