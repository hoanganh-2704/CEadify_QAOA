"""Tests for src/compact.py: decoders, the compact Hamiltonian, the circuit, the exact simulator and angles."""
import json

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector

from src.compact import (Reduced, angles_for, check_hamiltonian, choice_from_codes, codes_from_key,
                         compact_hamiltonian, compact_qaoa, cube_mixer, decode_tower, key_from_codes,
                         load_angles, ramp_angles, train_layerwise, transfer_table, uniform6,
                         valid_indices)
from src.puzzle import CHOICES, CUBES, all_solutions, cost_table, instance, tower_from, verify_choice

KNOWN_KEY = "011001100101"   # codes [5, 4, 1, 3]: one of the two answers of CUBES


def test_codes_from_known_key():
    codes = codes_from_key(KNOWN_KEY, 4)
    assert codes == [5, 4, 1, 3]
    assert verify_choice(CUBES, choice_from_codes(codes))
    assert codes_from_key("10" + KNOWN_KEY, 4) == codes          # plumbing characters on the left
    assert codes_from_key("0110 0110 0101", 4) == codes          # spaces are ignored


def test_reversed_key_is_not_an_answer():
    assert decode_tower(CUBES, KNOWN_KEY[::-1]) is None


def test_key_round_trip():
    rng = np.random.default_rng(7)
    for _ in range(20):
        codes = [int(k) for k in rng.integers(0, 8, 5)]
        assert codes_from_key(key_from_codes(codes), 5) == codes
        assert codes_from_key(key_from_codes(codes, n_extra=2), 5) == codes
    assert len(key_from_codes([1, 2], n_extra=1)) == 7


def test_invalid_codes_fail():
    assert choice_from_codes([5, 4, 6, 3]) is None
    assert choice_from_codes([7, 0, 0, 0]) is None
    assert decode_tower(CUBES, key_from_codes([5, 4, 6, 3])) is None


def test_decode_tower_on_both_answers():
    for choice in all_solutions(CUBES):
        codes = [CHOICES.index(tuple(c)) for c in choice]
        assert decode_tower(CUBES, key_from_codes(codes)) == tower_from(CUBES, choice)


@pytest.mark.parametrize("n, n_terms", [(3, 83), (4, 148), (5, 250)])
def test_check_hamiltonian(n, n_terms):
    report = check_hamiltonian(instance(n))
    assert report["n_terms"] == n_terms
    assert report["max_locality"] <= 4
    assert report["max_gap_valid"] < 1e-9
    assert report["zeros_valid"] == 2
    assert report["zeros_all"] == 2
    assert report["min_invalid"] >= 4
    assert report["min_nonzero"] == pytest.approx(2)


def test_penalty_only_touches_invalid_codes():
    with_pen = check_hamiltonian(CUBES, compact_hamiltonian(CUBES))
    without = check_hamiltonian(CUBES, compact_hamiltonian(CUBES, lam_invalid=0))
    assert without["max_gap_valid"] < 1e-9 and with_pen["max_gap_valid"] < 1e-9
    assert without["zeros_all"] > 2 and with_pen["zeros_all"] == 2
    assert with_pen["n_terms"] == without["n_terms"]


def test_valid_indices_match_cost_table():
    idx = valid_indices(3)
    assert len(set(idx.tolist())) == 216
    assert codes_from_key(format(int(idx[1 + 6 * 2]), "09b"), 3) == [1, 2, 0]


def test_uniform6():
    qc = QuantumCircuit(3)
    uniform6(qc, 0)
    probs = Statevector(qc).probabilities()
    assert np.allclose(probs[:6], 1 / 6, atol=1e-12)
    assert np.allclose(probs[6:], 0, atol=1e-12)


@pytest.mark.parametrize("beta", [0.4, 2.1])
def test_cube_mixer_is_the_valid_reflection(beta):
    qc = QuantumCircuit(3)
    cube_mixer(qc, beta, 0)
    U = Operator(qc).data
    u = np.full(6, 1 / np.sqrt(6))
    expected = np.eye(6) + (np.exp(-1j * beta) - 1) * np.outer(u, u)
    assert np.abs(U[:6, 6:]).max() < 1e-12 and np.abs(U[6:, :6]).max() < 1e-12   # no leakage
    assert np.allclose(U[:6, :6], expected, atol=1e-12)


def test_compact_qaoa_is_measurement_free_on_data_qubits():
    qc = compact_qaoa(CUBES, [0.3, 0.2], [0.5, 0.1])
    assert qc.num_qubits == 12
    assert "measure" not in qc.count_ops()


@pytest.mark.parametrize("n", [3, 4])
def test_reduced_matches_statevector(n):
    rng = np.random.default_rng(7)
    gammas, betas = rng.uniform(0, 3, 2), rng.uniform(0, 6, 2)
    cubes = instance(n)
    full = Statevector(compact_qaoa(cubes, gammas, betas)).probabilities()
    sim = Reduced(cubes)
    assert np.abs(full[valid_indices(n)] - sim.probs(gammas, betas)).max() < 1e-10
    assert 1 - full[valid_indices(n)].sum() < 1e-10
    assert np.array_equal(sim.cost, cost_table(cubes))


@pytest.mark.parametrize("p, expected", [(3, 0.0477), (12, 0.729), (24, 0.9854)])
def test_cached_angles(angles, p, expected):
    assert Reduced(CUBES).P(*angles_for(angles, p)) == pytest.approx(expected, abs=1e-3)
    assert angles[p]["P"] == pytest.approx(expected, abs=1e-3)


def test_fairness_angles_from_another_puzzle():
    alt = load_angles("results/angles_Cc_N4_alt57.json")
    assert Reduced(CUBES).P(*angles_for(alt, 24)) == pytest.approx(0.521, abs=1e-3)


def test_cvar_ladder_angles():
    cvar = load_angles("results/angles_Cc_N4_cvar.json")
    assert Reduced(CUBES).P(*angles_for(cvar, 3)) == pytest.approx(0.109, abs=1e-3)


def test_transfer_to_five_cubes(angles):
    table = transfer_table(angles, ns=(5,), ps=(24,))
    assert table[5][24] == pytest.approx(0.479, abs=1e-3)


def test_linear_ramp():
    with open("results/ramp_N4.json") as f:
        ramp = json.load(f)["24"]
    gammas, betas = ramp_angles(ramp["dg"], ramp["db"], 24)
    assert len(gammas) == len(betas) == 24
    assert Reduced(CUBES).P(gammas, betas) == pytest.approx(0.44, abs=0.01)


def test_train_layerwise_reproduces_p1(angles):
    out = train_layerwise(CUBES, 2, log=lambda *_: None)
    assert out[2]["P"] > out[1]["P"]
    assert out[1]["P"] == pytest.approx(angles[1]["P"], abs=2e-3)


def test_prepared_circuit_keeps_the_state(angles):
    runtime = pytest.importorskip("src.runtime")
    gammas, betas = angles_for(angles, 3)
    prepared = runtime.prepare_safe(compact_qaoa(CUBES, gammas, betas))
    psi = Statevector(prepared.remove_final_measurements(inplace=False)).data
    # data qubits are 1..12, q0 stays |0>, the marker q13 is |1>
    on_data = psi[(valid_indices(4) << 1) | (1 << 13)]
    fidelity = abs(np.vdot(Reduced(CUBES).state(gammas, betas), on_data)) ** 2
    assert fidelity > 1 - 1e-9


def test_train_cvar_ladder_reproduces_the_cvar_file():
    cached = load_angles("results/angles_Cc_N4_cvar.json")
    out = train_layerwise(CUBES, 2, objective="cvar_ladder", log=lambda *_: None)
    for p in (1, 2):
        assert out[p]["P"] == pytest.approx(cached[p]["P"], abs=1e-6)
