"""Round-5 checks, written by the student before running N = 5.
Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round5.py -q -p no:cacheprovider

The accepted recipe, unchanged, on the bonus puzzle make_puzzle(5, 16):
1. cost-0 legal picks == picks an independent solves() brute force finds, and
   their number == the starter's count_answers;
2. the reduced Hamiltonian's energy == the cost tensor on all 6^5 legal picks;
3. every reported P(solved) recomputes from its stored angles;
4. seeds are 0, 1, 2 and median/min/max come from those runs.
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

N, PUZZLE_SEED = 5, 16
SEEDS = [0, 1, 2]
TOL = 1e-9


@pytest.fixture(scope="module")
def cubes():
    return S.starter_puzzle(N, PUZZLE_SEED)


def legal_energies(H, n):
    """Energy of a Z/ZZ Hamiltonian on every one-hot pick, vectorized:
    each Pauli term contributes coeff * (-1)^(number of its Z qubits that are 1)."""
    picks = list(itertools.product(range(6), repeat=n))
    bits = np.zeros((len(picks), 6 * n), dtype=int)
    for row, pick in enumerate(picks):
        for c, k in enumerate(pick):
            bits[row, 6 * c + k] = 1
    z = H.paulis.z.astype(int)                      # terms x qubits, qubit 0 first
    signs = (-1.0) ** (bits @ z.T)
    return (signs @ H.coeffs.real).reshape((6,) * n)


def test_starter_functions_are_loaded_from_the_notebook():
    names = S.load_starter().keys()
    assert {"make_puzzle", "count_answers", "solves", "orientations"} <= set(names)


def test_cost_zero_picks_are_the_brute_force_solutions(cubes):
    costs = S.cost_tensor(cubes)
    zero = {tuple(i) for i in np.argwhere(np.isclose(costs, 0))}
    starter_solves = S.load_starter()["solves"]
    brute = {pick for pick in itertools.product(range(6), repeat=N)
             if starter_solves(S.tower_of(cubes, pick))}
    assert zero == brute
    assert len(zero) == S.load_starter()["count_answers"](cubes)
    assert len(zero) > 0


def test_reduced_energy_equals_cost_on_all_6_to_the_5_picks(cubes):
    H = S.reduced_hamiltonian(cubes, "best")
    assert H.num_qubits == 6 * N
    assert np.max(np.abs(legal_energies(H, N) - S.cost_tensor(cubes))) < TOL
    # spot-check the vectorized evaluation against solver.energy on one pick
    pick = (1, 4, 0, 5, 2)
    bits = [0] * (6 * N)
    for c, k in enumerate(pick):
        bits[6 * c + k] = 1
    assert S.energy(H, bits) == pytest.approx(S.cost_tensor(cubes)[pick], abs=TOL)


@pytest.fixture(scope="module")
def data():
    path = RESULTS / "round5.json"
    assert path.exists(), "write experiments/results/round5.json"
    return json.loads(path.read_text())


def test_round5_runs_the_accepted_recipe(data):
    assert (data["n"], data["puzzle_seed"]) == (N, PUZZLE_SEED)
    assert data["objective"] == "gibbs1" and data["mixer"] == "full"
    assert data["hamiltonian"] == "reduced_best"
    assert data["p"] == 7 and data["jitter"] == pytest.approx(0.05)
    assert [run["seed"] for run in data["runs"]] == SEEDS[: len(data["runs"])]
    assert len(data["runs"]) >= 1


def test_every_reported_p_solved_recomputes_from_its_angles(data, cubes):
    costs, mask = S.cost_tensor(cubes), S.solved_mask(cubes)
    values = []
    for run in data["runs"]:
        angles = np.array(run["angles"])
        p = len(angles) // 2
        psi = S.qaoa_state(costs, angles[:p], angles[p:], S.MIXERS["full"])
        recomputed = float((np.abs(psi) ** 2)[mask].sum())
        assert recomputed == pytest.approx(run["p_solved"], abs=TOL)
        values.append(recomputed)
    assert data["median"] == pytest.approx(float(np.median(values)), abs=TOL)
    assert data["min"] == pytest.approx(min(values), abs=TOL)
    assert data["max"] == pytest.approx(max(values), abs=TOL)
    assert data["qubits"] == 6 * N and data["cx_grading"] > 0 and data["depth_grading"] > 0
