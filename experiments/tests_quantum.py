"""Quantum checks for experiments/solver.py.

Run from the repo root (pytest collects this file when it is named explicitly):
    .venv\\Scripts\\python.exe -m pytest experiments/tests_quantum.py tests -q -p no:cacheprovider
"""
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


def circuit_vs_subspace(gammas, betas):
    """Max |p_circuit - p_subspace| over one-hot strings, mass outside one-hot, overlap."""
    H = S.choice_hamiltonian(CUBES_SMALL)
    costs = S.cost_tensor(CUBES_SMALL)
    circuit_sv = Statevector(S.tower_qaoa(CUBES_SMALL, H, gammas, betas))
    probs, outside = S.one_hot_probabilities(np.abs(circuit_sv.data) ** 2, N_SMALL)
    psi = S.qaoa_state(costs, gammas, betas)
    # Amplitude overlap (insensitive to the global phase dropped by cost_layer).
    amps = np.array([circuit_sv.data[sum(1 << (6 * c + k) for c, k in enumerate(idx))]
                     for idx in np.ndindex(psi.shape)])
    overlap = abs(np.vdot(amps, psi.ravel()))
    return float(np.max(np.abs(probs - np.abs(psi) ** 2))), outside, overlap


@pytest.mark.parametrize("seed", [0, 1, 2, 3])
def test_subspace_simulator_matches_circuit(seed):
    rng = np.random.default_rng(seed)
    gammas = rng.uniform(0, np.pi, 2)
    betas = rng.uniform(0, np.pi, 2)
    max_diff, outside, overlap = circuit_vs_subspace(gammas, betas)
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


@pytest.mark.parametrize("beta", [0.0, 0.3, 1.1, 2.9])
def test_closed_form_mixer_matches_qiskit_gates(beta):
    qc = QuantumCircuit(6)
    for i, j in S.MIX_PAIRS:
        qc.append(XXPlusYYGate(2 * beta), [i, j])
    keep = [1 << k for k in range(6)]
    restricted = Operator(qc).data[np.ix_(keep, keep)]
    assert np.allclose(restricted, S.xy_one_hot(beta), atol=TOL)
    assert np.allclose(restricted, S.xy_one_hot_fast(beta), atol=TOL)


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
