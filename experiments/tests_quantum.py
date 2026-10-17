"""Quantum checks for experiments/solver.py.

Run from the repo root (pytest collects this file when it is named explicitly):
    .venv\\Scripts\\python.exe -m pytest experiments/tests_quantum.py tests -q -p no:cacheprovider
"""
import itertools
import sys
from pathlib import Path

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import XXPlusYYGate
from qiskit.quantum_info import Operator, Statevector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tests"))

import solver as S  # noqa: E402
from notebook_loader import load_definitions  # noqa: E402

N_SMALL = 2
CUBES_SMALL = S.CUBES[:N_SMALL]
TOL = 1e-9
ROUND1_P_SOLVED = 0.2634623921  # notebook output 26.35%; round-1 harness value
HAMILTONIANS = {
    "full": S.choice_hamiltonian,
    "reduced": S.reduced_hamiltonian,
    "reduced_best": lambda cubes: S.reduced_hamiltonian(cubes, "best"),
}


def circuit_vs_subspace(gammas, betas, hamiltonian_fn=S.choice_hamiltonian, pairs=S.MIX_PAIRS):
    """Max |p_circuit - p_subspace| over one-hot strings, mass outside one-hot, overlap."""
    H = hamiltonian_fn(CUBES_SMALL)
    costs = S.cost_tensor(CUBES_SMALL)
    circuit_sv = Statevector(S.tower_qaoa(CUBES_SMALL, H, gammas, betas, pairs))
    probs, outside = S.one_hot_probabilities(np.abs(circuit_sv.data) ** 2, N_SMALL)
    psi = S.qaoa_state(costs, gammas, betas, pairs)
    # Amplitude overlap (insensitive to the global phase dropped by cost_layer).
    amps = np.array([circuit_sv.data[S.one_hot_index(idx)] for idx in np.ndindex(psi.shape)])
    overlap = abs(np.vdot(amps, psi.ravel()))
    return float(np.max(np.abs(probs - np.abs(psi) ** 2))), outside, overlap


@pytest.mark.parametrize("mixer", sorted(S.MIXERS))
@pytest.mark.parametrize("hamiltonian", sorted(HAMILTONIANS))
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_subspace_simulator_matches_circuit(seed, hamiltonian, mixer):
    rng = np.random.default_rng(seed)
    gammas = rng.uniform(0, np.pi, 2)
    betas = rng.uniform(0, np.pi, 2)
    max_diff, outside, overlap = circuit_vs_subspace(
        gammas, betas, HAMILTONIANS[hamiltonian], S.MIXERS[mixer])
    assert max_diff < TOL
    assert abs(outside) < TOL
    assert overlap == pytest.approx(1.0, abs=TOL)


def test_w_state_is_uniform_over_one_hot():
    qc = QuantumCircuit(6)
    S.w_state(qc, list(range(6)))
    probs = np.abs(Statevector(qc).data) ** 2
    one_hot = [1 << k for k in range(6)]
    assert np.allclose(probs[one_hot], 1 / 6, atol=TOL)
    assert probs.sum() - probs[one_hot].sum() < TOL


@pytest.mark.parametrize("mixer", sorted(S.MIXERS))
@pytest.mark.parametrize("beta", [0.0, 0.3, 1.1, 2.9])
def test_mixer_matrices_match_qiskit_gates(beta, mixer):
    pairs = S.MIXERS[mixer]
    qc = QuantumCircuit(6)
    for i, j in pairs:
        qc.append(XXPlusYYGate(2 * beta), [i, j])
    keep = [1 << k for k in range(6)]
    restricted = Operator(qc).data[np.ix_(keep, keep)]
    assert np.allclose(restricted, S.xy_one_hot(beta, pairs), atol=TOL)
    assert np.allclose(restricted, S.xy_one_hot_fast(beta, pairs), atol=TOL)


def test_decoder_uses_qiskit_bit_order():
    # Cube 0 choice 3 -> qubit 3; cube 1 choice 5 -> qubit 11. Qubit 0 is rightmost.
    bits = ["0"] * 12
    bits[3] = bits[11] = "1"
    assert S.decode("".join(reversed(bits)), 2) == [3, 5]
    assert S.decode("0" * 12, 2) is None


def test_solver_reproduces_notebook_model():
    nb = load_definitions()
    assert np.array_equal(S.cost_tensor(S.CUBES), nb["cost_tensor"](nb["CUBES"]))
    H_mine = S.choice_hamiltonian(S.CUBES)
    H_nb = nb["choice_hamiltonian"](nb["CUBES"])
    assert H_mine.equiv(H_nb) and len(H_mine) == len(H_nb) == 290
    for beta in (0.2, 1.3):
        assert np.allclose(S.xy_one_hot(beta), nb["xy_one_hot"](beta), atol=TOL)


def test_solved_mask_agrees_with_zero_cost():
    mask = S.solved_mask(S.CUBES)
    assert int(mask.sum()) == 2
    assert np.array_equal(mask, np.isclose(S.cost_tensor(S.CUBES), 0))


# ---------------------------------------------------------------- round 2: reduced Hamiltonian

@pytest.mark.parametrize("gauge, n_zz", [("reference0", 94), ("best", 77)])
def test_reduced_hamiltonian_equals_cost_on_all_legal_picks(gauge, n_zz):
    H = S.reduced_hamiltonian(S.CUBES, gauge)
    costs = S.cost_tensor(S.CUBES)
    worst = 0.0
    for index in itertools.product(range(6), repeat=len(S.CUBES)):
        bits = [0] * H.num_qubits
        for c, k in enumerate(index):
            bits[6 * c + k] = 1
        worst = max(worst, abs(S.energy(H, bits) - costs[index]))
    assert worst < TOL
    assert S.term_counts(H)["ZZ"] == n_zz
    # No ZZ term inside a cube: those are constant on the one-hot subspace.
    for label in H.paulis.to_labels():
        qubits = [q for q, op in enumerate(reversed(label)) if op == "Z"]
        assert len({q // 6 for q in qubits}) == len(qubits)


def test_costs_are_even_integers_so_gamma_is_pi_periodic():
    costs = S.cost_tensor(S.CUBES)
    assert np.array_equal(costs % 2, np.zeros_like(costs))
    psi_a = S.qaoa_state(costs, [0.4, 1.0], [0.2, 0.3])
    psi_b = S.qaoa_state(costs, [0.4 + np.pi, 1.0 - np.pi], [0.2, 0.3])
    assert np.allclose(psi_a, psi_b, atol=TOL)


@pytest.fixture(scope="module")
def round1_angles():
    costs, mask = S.cost_tensor(S.CUBES), S.solved_mask(S.CUBES)
    angles, curve = S.train_layerwise(costs, mask, 7)
    return angles, curve[-1][2]


def test_round1_training_reproduces_notebook(round1_angles):
    _, p_solved = round1_angles
    assert p_solved == pytest.approx(ROUND1_P_SOLVED, abs=1e-9)


def test_reduced_circuit_cx_budget(round1_angles):
    angles, _ = round1_angles
    H = S.reduced_hamiltonian(S.CUBES)
    circuit = S.tower_qaoa(S.CUBES, H, angles[:7], angles[7:])
    _, level1 = S.transpile_metrics(circuit, 1)
    _, grading = S.transpile_metrics(circuit, None)
    assert level1["cx"] <= 2250
    assert grading["cx"] <= 2230


# ---------------------------------------------------------------- round 2: objectives

def test_objectives_on_a_known_distribution():
    costs = np.array([0.0, 2.0, 4.0, 6.0])
    probs = np.array([0.05, 0.10, 0.35, 0.50])
    assert S.objective_average(probs, costs) == pytest.approx(4.6)
    # Lowest 10% of the mass: 0.05 at cost 0 and 0.05 at cost 2 -> mean 1.0.
    assert S.objective_cvar(probs, costs, 0.1) == pytest.approx(1.0)
    expected = -np.log(np.sum(probs * np.exp(-costs)))
    assert S.objective_gibbs(probs, costs, 1.0) == pytest.approx(expected)
