"""Classical checks of the model in solution.ipynb.

Each test compares the notebook's code with an independent implementation:
a brute force built from real cube rotations, a degree count with Counter,
and a Hamiltonian evaluation that reads Qiskit's qubit-indexed Z arrays
instead of label strings.
"""
import itertools
from collections import Counter

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from notebook_loader import load_definitions

NB = load_definitions()
CUBES = NB["CUBES"]
CHOICES = NB["CHOICES"]
BONUS_SEEDS = {5: 16, 6: 86, 7: 68, 8: 4}

# Face slots: 0 front, 1 back, 2 left, 3 right, 4 top, 5 bottom.
# Slot s holds a face id; face id f belongs to opposite pair f // 2.
TURN_VERTICAL = (3, 2, 0, 1, 4, 5)   # quarter turn about the top-bottom axis
TURN_SIDEWAYS = (4, 5, 2, 3, 1, 0)   # quarter turn about the left-right axis


# ---------------------------------------------------------------- independent model

def rotations():
    """All placements of face ids 0..5 reachable by rotating a cube (BFS)."""
    start = tuple(range(6))
    seen, frontier = {start}, [start]
    while frontier:
        state = frontier.pop()
        for move in (TURN_VERTICAL, TURN_SIDEWAYS):
            nxt = tuple(state[move[s]] for s in range(6))
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
    return sorted(seen)


def face_colours(cube):
    """Face id 2p and 2p+1 are the two colours of opposite pair p."""
    return [cube[f // 2][f % 2] for f in range(6)]


def brute_force(cubes):
    """Every solved tower, as one rotation (tuple of face ids) per cube."""
    rots = rotations()
    colours = [face_colours(cube) for cube in cubes]
    solved = []
    for combo in itertools.product(rots, repeat=len(cubes)):
        sides_ok = all(
            len({colours[c][combo[c][side]] for c in range(len(cubes))}) == len(cubes)
            for side in range(4)
        )
        if sides_ok:
            solved.append(combo)
    return solved


def choice_of(rotation):
    """(front/back pair, left/right pair) used by a rotation."""
    return (rotation[0] // 2, rotation[2] // 2)


def is_solution(cubes, choice_indices):
    """Both axes are 2-factors, counted with Counter."""
    for axis in (0, 1):
        degree = Counter()
        for cube, k in zip(cubes, choice_indices):
            degree.update(cube[CHOICES[k][axis]])
        letters = {ch for cube in cubes for pair in cube for ch in pair}
        if any(degree[ch] != 2 for ch in letters):
            return False
    return True


def degree_cost(cubes, choice_indices):
    letters = {ch for cube in cubes for pair in cube for ch in pair}
    total = 0
    for axis in (0, 1):
        degree = Counter()
        for cube, k in zip(cubes, choice_indices):
            degree.update(cube[CHOICES[k][axis]])
        total += sum((degree[ch] - 2) ** 2 for ch in letters)
    return total


def z_energy(hamiltonian, bits):
    """Evaluate a Z-only operator from its qubit-indexed z array."""
    bits = np.asarray(bits, dtype=bool)
    z = hamiltonian.paulis.z
    signs = np.where(np.sum(z & bits, axis=1) % 2 == 1, -1.0, 1.0)
    return float(np.real(hamiltonian.coeffs) @ signs)


def one_hot_bits(choice_indices):
    bits = [0] * (6 * len(choice_indices))
    for c, k in enumerate(choice_indices):
        bits[6 * c + k] = 1
    return bits


@pytest.fixture(scope="module")
def cost():
    return NB["cost_tensor"](CUBES)


@pytest.fixture(scope="module")
def solved_rotations():
    return brute_force(CUBES)


# ---------------------------------------------------------------- the four-cube puzzle

def test_a_cube_has_24_rotations():
    assert len(rotations()) == 24


def test_brute_force_finds_eight_solved_towers(solved_rotations):
    assert len(solved_rotations) == 8


def test_choices_are_the_six_ordered_pairs_of_distinct_pairs():
    assert sorted(CHOICES) == sorted(itertools.permutations(range(3), 2))
    assert {choice_of(r) for r in rotations()} == set(CHOICES)


def test_cost_zero_set_equals_brute_force(cost, solved_rotations):
    from_brute_force = {
        tuple(CHOICES.index(choice_of(r)) for r in combo) for combo in solved_rotations
    }
    from_cost = {tuple(int(i) for i in idx) for idx in zip(*np.where(np.isclose(cost, 0)))}
    assert from_cost == from_brute_force
    assert len(from_cost) == 2


def test_cost_tensor_matches_independent_degree_cost(cost):
    for idx in itertools.product(range(6), repeat=len(CUBES)):
        assert cost[idx] == degree_cost(CUBES, idx)


def test_only_answers_score_zero_and_gap_is_two(cost):
    for idx in itertools.product(range(6), repeat=len(CUBES)):
        assert (cost[idx] == 0) == is_solution(CUBES, idx)
    assert np.unique(cost)[1] == 2


def test_cost_tensor_matches_starter_qubo(cost):
    starter_cost, one_hot = NB["starter_cost"], NB["one_hot"]
    for idx in itertools.product(range(6), repeat=len(CUBES)):
        x = [one_hot(CHOICES[k][0]) for k in idx]
        y = [one_hot(CHOICES[k][1]) for k in idx]
        assert starter_cost(CUBES, x, y) == cost[idx]


def test_every_cost_zero_pick_builds_a_solved_tower(cost):
    for idx in zip(*np.where(np.isclose(cost, 0))):
        assert NB["solves"](NB["tower_of"](CUBES, [int(i) for i in idx]))


def test_nonzero_picks_never_build_a_solved_tower(cost):
    for idx in itertools.product(range(6), repeat=len(CUBES)):
        if cost[idx] > 0:
            assert not NB["solves"](NB["tower_of"](CUBES, idx))


# ---------------------------------------------------------------- the Hamiltonian

@pytest.fixture(scope="module")
def hamiltonian():
    return NB["choice_hamiltonian"](CUBES)


def test_hamiltonian_is_diagonal_and_at_most_quadratic(hamiltonian):
    assert hamiltonian.num_qubits == 24
    assert not hamiltonian.paulis.x.any()
    assert hamiltonian.paulis.z.sum(axis=1).max() <= 2
    assert np.allclose(np.imag(hamiltonian.coeffs), 0)


def test_hamiltonian_equals_cost_on_every_one_hot_string(hamiltonian, cost):
    for idx in itertools.product(range(6), repeat=len(CUBES)):
        assert z_energy(hamiltonian, one_hot_bits(idx)) == pytest.approx(cost[idx], abs=1e-9)


def test_notebook_energy_agrees_with_z_array_evaluation(hamiltonian):
    rng = np.random.default_rng(7)
    for _ in range(200):
        bits = rng.integers(0, 2, 24).tolist()
        assert NB["energy"](hamiltonian, bits) == pytest.approx(z_energy(hamiltonian, bits))


def test_hamiltonian_ground_energy_is_zero_on_one_hot_space(hamiltonian):
    energies = [z_energy(hamiltonian, one_hot_bits(idx))
                for idx in itertools.product(range(6), repeat=len(CUBES))]
    assert min(energies) == pytest.approx(0)
    assert sum(np.isclose(energies, 0)) == 2


# ---------------------------------------------------------------- decoding (Qiskit bit order)

@pytest.mark.parametrize("choice", [(3, 1, 4, 5), (5, 4, 1, 3), (0, 2, 5, 1)])
def test_decoder_reads_qiskit_bit_order(choice):
    qc = QuantumCircuit(24)
    for c, k in enumerate(choice):
        qc.x(6 * c + k)
    (bitstring,) = Statevector(qc).probabilities_dict().keys()
    assert NB["choices_from_bitstring"](bitstring, 4) == list(choice)


def test_decoder_rejects_strings_that_are_not_one_hot():
    assert NB["choices_from_bitstring"]("0" * 24, 4) is None
    assert NB["choices_from_bitstring"]("1" * 24, 4) is None


# ---------------------------------------------------------------- improvement 1: reduced Hamiltonian

@pytest.fixture(scope="module")
def small_hamiltonian():
    return NB["reduced_hamiltonian"](CUBES)


def test_cost_splits_into_one_and_two_cube_tables_exactly(cost):
    base, single, pair = NB["one_hot_decomposition"](CUBES)
    for idx in itertools.product(range(6), repeat=len(CUBES)):
        rebuilt = base + sum(single[c][k] for c, k in enumerate(idx))
        rebuilt += sum(pair[c, d][idx[c], idx[d]] for c, d in itertools.combinations(range(4), 2))
        assert rebuilt == pytest.approx(cost[idx], abs=1e-9)


def test_reduced_hamiltonian_is_diagonal_and_at_most_quadratic(small_hamiltonian):
    assert small_hamiltonian.num_qubits == 24
    assert not small_hamiltonian.paulis.x.any()
    assert small_hamiltonian.paulis.z.sum(axis=1).max() <= 2


def test_reduced_hamiltonian_equals_cost_on_every_one_hot_string(small_hamiltonian, cost):
    for idx in itertools.product(range(6), repeat=len(CUBES)):
        assert z_energy(small_hamiltonian, one_hot_bits(idx)) == pytest.approx(cost[idx], abs=1e-9)


def test_reduced_hamiltonian_has_fewer_two_qubit_terms(small_hamiltonian, hamiltonian):
    assert NB["zz_count"](small_hamiltonian) < NB["zz_count"](hamiltonian)


def test_reduced_hamiltonian_has_no_same_cube_zz(small_hamiltonian):
    for row in small_hamiltonian.paulis.z:
        qubits = np.flatnonzero(row)
        if len(qubits) == 2:
            assert qubits[0] // 6 != qubits[1] // 6


@pytest.mark.parametrize("n,seed", [(5, 16), (6, 86)])
def test_reduced_hamiltonian_is_exact_on_bonus_puzzles(n, seed):
    puzzle = NB["make_puzzle"](n, seed)
    tensor = NB["cost_tensor"](puzzle)
    reduced = NB["reduced_hamiltonian"](puzzle)
    rng = np.random.default_rng(seed)
    for _ in range(300):
        idx = tuple(int(k) for k in rng.integers(0, 6, n))
        assert z_energy(reduced, one_hot_bits(idx)) == pytest.approx(tensor[idx], abs=1e-9)


# ---------------------------------------------------------------- improvement 2: Gibbs objective

def test_gibbs_objective_depends_only_on_the_cost_histogram(cost):
    gibbs = NB["gibbs_objective"]
    rng = np.random.default_rng(7)
    probs = rng.random(cost.shape)
    probs /= probs.sum()
    shuffled = probs.copy()
    for value in np.unique(cost):  # move probability around inside each equal-cost group
        group = np.flatnonzero(cost.ravel() == value)
        shuffled.ravel()[group] = rng.permutation(probs.ravel()[group])
    assert gibbs(shuffled, cost) == pytest.approx(gibbs(probs, cost), abs=1e-12)


def test_gibbs_objective_rewards_moving_weight_to_cost_zero(cost):
    gibbs = NB["gibbs_objective"]
    uniform = np.full(cost.shape, 1 / cost.size)
    better = uniform.copy()
    zero, worst = np.flatnonzero(cost.ravel() == 0)[0], np.argmax(cost.ravel())
    better.ravel()[zero] += better.ravel()[worst]
    better.ravel()[worst] = 0
    assert gibbs(better, cost) < gibbs(uniform, cost)
    assert gibbs(np.where(cost == 0, 0.5, 0.0), cost) == pytest.approx(-np.log(1.0), abs=1e-12)


# ---------------------------------------------------------------- bonus puzzles

@pytest.mark.parametrize("n,seed", sorted(BONUS_SEEDS.items()))
def test_bonus_seed_has_exactly_one_tower(n, seed):
    puzzle = NB["make_puzzle"](n, seed)
    tensor = NB["cost_tensor"](puzzle)
    zeros = [tuple(int(i) for i in idx) for idx in zip(*np.where(np.isclose(tensor, 0)))]
    assert len(zeros) == 2
    for idx in zeros:
        assert is_solution(puzzle, idx)
        assert NB["solves"](NB["tower_of"](puzzle, idx))


@pytest.mark.parametrize("n,seed", [(5, 16), (6, 86)])
def test_bonus_cost_tensor_matches_independent_count(n, seed):
    puzzle = NB["make_puzzle"](n, seed)
    tensor = NB["cost_tensor"](puzzle)
    rng = np.random.default_rng(seed)
    for _ in range(2000):
        idx = tuple(int(k) for k in rng.integers(0, 6, n))
        assert tensor[idx] == degree_cost(puzzle, idx)
