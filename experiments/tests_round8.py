"""Round-8 checks, written by the student before freezing the hardware circuit.
Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round8.py -q -p no:cacheprovider

The file results/hardware_n3_p1.qasm (make_puzzle(3, 0), p = 1, saved round-7 angles,
built with resources.helpers.prepare: marker qubit 18 fixed at 1, every qubit measured):
1. round trip: its state equals the exact subspace state at the saved angles (to 1e-9,
   up to a global phase) with the marker at 1 and no weight outside one-hot;
2. its GRADING-call CX count equals round 7's p = 1 cx_grading;
3. bit order: hand-made counts give the right solved/kept/total, and reversed keys
   are either restored by the marker or not counted as solved;
4. noiseless Aer on the loaded file is within 3 sigma of exact and 100% one-hot, and
   round 7's saved noisy p = 1 counts reproduce the saved row through the new function.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
QASM = RESULTS / "hardware_n3_p1.qasm"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

N, MARKER = 3, 18
SHOTS = 2000
TOL = 1e-9


@pytest.fixture(scope="module")
def round7():
    data = json.loads((RESULTS / "round7.json").read_text())
    row = next(r for r in data["rows"] if r["p"] == 1)
    return data, row


@pytest.fixture(scope="module")
def cubes(round7):
    return S.starter_puzzle(N, round7[0]["puzzle_seed"])


@pytest.fixture(scope="module")
def loaded():
    assert QASM.exists(), "write experiments/results/hardware_n3_p1.qasm"
    return S.load_qasm(QASM)


def key(pick, marker=True):
    """Qiskit-order key (qubit 0 rightmost) for a legal pick, with the marker as qubit 18."""
    bits = ["0"] * (6 * N)
    for c, k in enumerate(pick):
        bits[6 * c + k] = "1"
    body = "".join(reversed(bits))
    return ("1" + body) if marker else body


def solved_and_unsolved(cubes):
    mask = S.solved_mask(cubes)
    solved = tuple(int(i) for i in np.argwhere(mask)[0])
    unsolved = tuple(int(i) for i in np.argwhere(~mask)[0])
    return solved, unsolved


# ---------------------------------------------------------------- 1. round trip

def test_loaded_state_matches_exact_subspace_state(loaded, round7, cubes):
    angles = np.array(round7[1]["angles"])
    psi = S.qaoa_state(S.cost_tensor(cubes), angles[:1], angles[1:], S.MIXERS["full"])
    circuit = loaded.remove_final_measurements(inplace=False)
    assert circuit.num_qubits == 6 * N + 1
    amps = Statevector(circuit).data
    legal = [S.one_hot_index(idx) + (1 << MARKER) for idx in np.ndindex(psi.shape)]
    assert abs(np.vdot(amps[legal], psi.ravel())) == pytest.approx(1.0, abs=TOL)
    assert float(np.sum(np.abs(amps) ** 2) - np.sum(np.abs(amps[legal]) ** 2)) < TOL


def test_file_is_reproducible_from_the_saved_angles(round7, cubes):
    angles = np.array(round7[1]["angles"])
    rebuilt = S.qasm_text(S.hardware_circuit(cubes, angles))
    assert rebuilt == QASM.read_text()


# ---------------------------------------------------------------- 2. gate count

def test_grading_cx_equals_round7_p1(loaded, round7):
    _, metrics = S.transpile_metrics(loaded.remove_final_measurements(inplace=False), None)
    assert metrics["cx"] == round7[1]["cx_grading"]


# ---------------------------------------------------------------- 3. bit order

def test_hand_made_counts_decode_with_qiskit_order(cubes):
    solved = solved_with_qubit0_off(cubes)
    unsolved = next(tuple(int(i) for i in idx) for idx in np.argwhere(~S.solved_mask(cubes))
                    if idx[0] != 0)
    counts = {key(solved): 5, key(unsolved): 3, "1" + "0" * 18: 2}   # last: marker only
    row = S.results_row(counts, cubes, marker=True)
    assert (row["solved"], row["kept"], row["total"]) == (5, 8, 10)


def solved_with_qubit0_off(cubes):
    """A solved pick whose cube 0 is not choice 0, so qubit 0 reads 0 and cannot pose
    as the marker."""
    return next(tuple(int(i) for i in idx) for idx in np.argwhere(S.solved_mask(cubes))
                if idx[0] != 0)


def test_reversed_keys_are_restored_by_the_marker_or_not_counted(cubes):
    solved, _ = solved_and_unsolved(cubes)
    clean = solved_with_qubit0_off(cubes)
    # Whole key reversed (a provider listing qubit 0 first): only the marker end is always 1,
    # so the reversal is detected and undone.
    flipped = S.results_row({key(solved)[::-1]: 4, key(clean)[::-1]: 6}, cubes, marker=True)
    assert flipped["solved"] == 10
    # Body reversed without a marker to reveal it: the solved pick must not count as solved.
    body = key(solved, marker=False)
    assert body[::-1] != body
    wrong = S.results_row({body[::-1]: 4}, cubes, marker=False)
    assert wrong["solved"] == 0


def test_marker_read_as_zero_is_dropped_not_fatal(cubes):
    clean = solved_with_qubit0_off(cubes)
    counts = {key(clean): 9, "0" + key(clean)[1:]: 1}       # one readout flip on the marker
    row = S.results_row(counts, cubes, marker=True)
    assert row["marker_dropped"] == 1 and row["total"] == 9 and row["solved"] == 9


def test_ambiguous_marker_end_raises_instead_of_guessing(cubes):
    solved, _ = solved_and_unsolved(cubes)          # cube 0 is choice 0: qubit 0 reads 1
    assert key(solved)[0] == "1" and key(solved)[-1] == "1"
    with pytest.raises(ValueError):
        S.results_row({key(solved): 4}, cubes, marker=True)


# ---------------------------------------------------------------- 4. pipeline on simulated counts

def test_noiseless_aer_on_loaded_file(loaded, round7, cubes):
    counts = S.run_loaded(loaded, shots=SHOTS, seed=7)
    row = S.results_row(counts, cubes, marker=True)
    exact = round7[1]["exact_p"]
    sigma = math.sqrt(exact * (1 - exact) / SHOTS)
    assert row["total"] == SHOTS and row["kept"] == SHOTS
    assert abs(row["p_all"] - exact) <= 3 * sigma


def test_round7_noisy_counts_reproduce_the_saved_row(round7, cubes):
    saved = round7[1]["noisy"]
    row = S.results_row(saved["counts"], cubes, marker=False)
    assert (row["total"], row["kept"], row["solved"]) == \
        (saved["shots"], saved["one_hot"], saved["solved"])
    assert row["p_all"] == pytest.approx(saved["p_solved"], abs=TOL)
    assert row["p_post_selected"] == pytest.approx(saved["p_post_selected"], abs=TOL)


def test_round8_json_records_the_file_hash(round7):
    data = json.loads((RESULTS / "round8.json").read_text())
    assert data["qasm_sha256"] == hashlib.sha256(QASM.read_bytes()).hexdigest()
    assert data["qubits"] == 6 * N + 1
    assert data["random_legal"] == pytest.approx(round7[0]["random_legal"])
