"""Teacher's round-2 checks (reduced Hamiltonian only). Written by the teacher; the student
must not edit this file. Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round2_review.py -q -p no:cacheprovider

The pass condition is the invariant, not a gate count:
  1. the reduced energy equals cost_tensor on every legal pick;
  2. at the SAVED round-1 angles (results/round1.json, not retrained) the reduced
     circuit's state equals the round-1 circuit's state up to a global phase;
  3. the round-2 results record that they used exactly those saved angles;
  4. the student's round note exists and explains the round in their own words.
"""
import itertools
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

TOL = 1e-9
GAUGES = ["reference0", "best"]


def saved_round1_angles():
    return np.array(json.loads((RESULTS / "round1.json").read_text())["rows"][0]["angles"])


def energies_on_legal_picks(H, n_cubes):
    """Energy of H on every one-hot pick, as a (6,)*n tensor."""
    out = np.zeros((6,) * n_cubes)
    for index in itertools.product(range(6), repeat=n_cubes):
        bits = [0] * H.num_qubits
        for c, k in enumerate(index):
            bits[6 * c + k] = 1
        out[index] = S.energy(H, bits)
    return out


@pytest.mark.parametrize("gauge", GAUGES)
def test_reduced_energy_equals_cost_on_all_1296_legal_picks(gauge):
    H = S.reduced_hamiltonian(S.CUBES, gauge)
    worst = np.max(np.abs(energies_on_legal_picks(H, 4) - S.cost_tensor(S.CUBES)))
    assert worst < TOL


@pytest.mark.parametrize("gauge", GAUGES)
def test_legal_state_matches_round1_circuit_at_saved_angles_n4(gauge):
    """N=4, saved angles: the cost layer acts on the legal subspace through H's energies
    there, so feed each Hamiltonian's own energies to the subspace simulator."""
    angles = saved_round1_angles()
    p = len(angles) // 2
    psi_old = S.qaoa_state(energies_on_legal_picks(S.choice_hamiltonian(S.CUBES), 4),
                           angles[:p], angles[p:])
    psi_new = S.qaoa_state(energies_on_legal_picks(S.reduced_hamiltonian(S.CUBES, gauge), 4),
                           angles[:p], angles[p:])
    assert abs(np.vdot(psi_old.ravel(), psi_new.ravel())) == pytest.approx(1.0, abs=TOL)


@pytest.mark.parametrize("gauge", GAUGES)
def test_full_circuits_agree_at_saved_angles_n2(gauge):
    """N=2 (12 qubits), saved round-1 angles, real Qiskit circuits: old vs reduced H."""
    cubes = S.CUBES[:2]
    angles = saved_round1_angles()
    p = len(angles) // 2
    old = Statevector(S.tower_qaoa(cubes, S.choice_hamiltonian(cubes), angles[:p], angles[p:]))
    new = Statevector(S.tower_qaoa(cubes, S.reduced_hamiltonian(cubes, gauge),
                                   angles[:p], angles[p:]))
    assert abs(np.vdot(old.data, new.data)) == pytest.approx(1.0, abs=TOL)


def test_round2_results_used_the_saved_round1_angles():
    """results/round2.json must contain "angles_used": the exact vector from round1.json."""
    data = json.loads((RESULTS / "round2.json").read_text())
    assert "angles_used" in data, "round2.json does not record the angles it used"
    assert np.max(np.abs(np.array(data["angles_used"]) - saved_round1_angles())) < 1e-12


def test_round2_note_explains_the_round():
    """results/round2_note.md: at least four sentences in the student's own words."""
    note = RESULTS / "round2_note.md"
    assert note.exists(), "write experiments/results/round2_note.md"
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", note.read_text(encoding="utf-8").strip())
                 if len(s.split()) >= 5]
    assert len(sentences) >= 4
