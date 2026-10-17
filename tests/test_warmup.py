"""Tests for src/warmup.py: starter Hamiltonians, the generalised cost layer, the warm-up QAOA and decoders."""
import numpy as np
import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import PauliEvolutionGate
from qiskit.quantum_info import SparsePauliOp, Statevector
from qiskit_aer import AerSimulator

from src.compact import angles_for, compact_hamiltonian, load_angles
from src.puzzle import (CUBES, all_solutions, cost, diagonal, front_back, make_puzzle, one_hot,
                        verify_choice)
from src.warmup import (build_hamiltonian, constrained_qaoa, cost_layer, decode_frontback,
                        decode_onehot, energy, front_back_hamiltonian, good_strings, onehot_qaoa,
                        optimise_warmup, scan, to_bits)

KNOWN_KEYS = ["010100001100100001100010", "100010100001001100010100"]   # the two answers, 6N layout


def test_build_hamiltonian_matches_cost():
    H = build_hamiltonian(CUBES)
    assert H.num_qubits == 24 and len(H) == 153
    rng = np.random.default_rng(7)
    for _ in range(200):
        x = rng.integers(0, 2, (4, 3)).tolist()
        y = rng.integers(0, 2, (4, 3)).tolist()
        assert energy(H, to_bits(x, y)) == pytest.approx(cost(CUBES, x, y), abs=1e-9)
    for key in KNOWN_KEYS:
        assert energy(H, [int(b) for b in key[::-1]]) == pytest.approx(0, abs=1e-9)


def test_front_back_hamiltonian():
    H = front_back_hamiltonian(CUBES)
    assert H.num_qubits == 12 and len(H) == 68
    values = diagonal(H)
    one_hot_keys = [i for i in range(4096)
                    if all(bin((i >> (3 * c)) & 7).count("1") == 1 for c in range(4))]
    zeros = {format(i, "012b") for i in one_hot_keys if abs(values[i]) < 1e-9}
    assert zeros == set(good_strings(CUBES))
    assert (np.abs(diagonal(front_back_hamiltonian(CUBES, lam=2))) < 1e-9).sum() == 4


def test_bonus_letters_are_used():
    cubes = make_puzzle(5, 16)
    choice = all_solutions(cubes)[0]
    bits = to_bits([one_hot(fb) for fb, _ in choice], [one_hot(lr) for _, lr in choice])
    assert energy(build_hamiltonian(cubes), bits) == pytest.approx(0, abs=1e-9)
    assert energy(build_hamiltonian(cubes, colours="RGBY"), bits) != pytest.approx(0, abs=1e-9)
    H = build_hamiltonian(cubes)
    for c in range(5):
        assert any(label[::-1][6 * c:6 * c + 6].count("Z") for label in H.paulis.to_labels())


@pytest.mark.parametrize("gamma", [0.3, 2.8])
def test_cost_layer_equals_pauli_evolution(gamma):
    H = compact_hamiltonian(CUBES)          # has 3- and 4-body terms
    start = QuantumCircuit(12)
    start.h(range(12))
    ours = start.copy()
    cost_layer(ours, H, gamma)
    reference = start.copy()
    reference.append(PauliEvolutionGate(H, time=gamma), range(12))
    a, b = Statevector(ours).data, Statevector(reference).data
    assert abs(np.vdot(a, b)) ** 2 > 1 - 1e-10


def _starter_cost_layer(qc, H, gamma):
    """The starter's cost_layer, copied verbatim, for comparison."""
    for label, coeff in zip(H.paulis.to_labels(), H.coeffs):
        qubits = [q for q, op in enumerate(reversed(label)) if op == "Z"]
        if len(qubits) == 1:
            qc.rz(2 * gamma * coeff.real, qubits[0])
        elif len(qubits) == 2:
            qc.rzz(2 * gamma * coeff.real, *qubits)


def test_cost_layer_matches_starter_on_two_local():
    H = front_back_hamiltonian(CUBES, lam=2)
    ours, starter = QuantumCircuit(12), QuantumCircuit(12)
    cost_layer(ours, H, 0.7)
    _starter_cost_layer(starter, H, 0.7)
    assert set(ours.count_ops()) <= {"rz", "rzz"}
    assert ours.count_ops() == starter.count_ops()


def test_three_body_term_is_not_dropped():
    H = SparsePauliOp.from_sparse_list([("ZZZ", [0, 1, 2], 1.0)], 3)
    plus = QuantumCircuit(3)
    plus.h(range(3))
    qc = plus.copy()
    cost_layer(qc, H, 0.4)
    after, before = Statevector(qc), Statevector(plus)
    assert abs(np.vdot(after.data, before.data)) ** 2 < 1 - 1e-3
    phases = np.exp(-1j * 0.4 * diagonal(H))
    assert np.allclose(after.data, phases * before.data, atol=1e-12)


def test_warmup_reproduces_starter_numbers():
    H = front_back_hamiltonian(CUBES)
    good = good_strings(CUBES)
    wins = [int(s, 2) for s in good]
    gammas, betas = np.linspace(0, np.pi, 41), np.linspace(0, np.pi, 41)
    avg, hit = scan(H, gammas, betas, good)
    i, j = np.unravel_index(avg.argmin(), avg.shape)
    assert (gammas[i], betas[j]) == pytest.approx((2.827, 0.236), abs=1e-3)
    assert hit[i, j] == pytest.approx(0.188, abs=0.002)
    best, history = optimise_warmup(H, [gammas[i], gammas[i], betas[j], betas[j]])
    assert len(history) <= 200
    probs = Statevector(constrained_qaoa(H, best[:2], best[2:])).probabilities()
    assert probs[wins].sum() == pytest.approx(0.284, abs=0.005)


def test_decode_onehot_known_keys():
    choices = [decode_onehot(key, 4) for key in KNOWN_KEYS]
    assert all(verify_choice(CUBES, c) for c in choices)
    assert sorted(choices) == sorted(all_solutions(CUBES))
    for key in KNOWN_KEYS:
        reversed_choice = decode_onehot(key[::-1], 4)
        assert reversed_choice is None or not verify_choice(CUBES, reversed_choice)
    assert decode_onehot("0" * 24, 4) is None
    assert decode_onehot("11" + KNOWN_KEYS[0], 4) == choices[0]


def test_decode_frontback():
    assert [tuple(decode_frontback(s, 4)) for s in good_strings(CUBES)] == front_back
    assert decode_frontback("011" + "001" * 3, 4) is None


def test_onehot_qaoa_stays_one_hot_and_matches_cached_angles():
    angles = load_angles("results/angles_B_N4.json")
    qc = onehot_qaoa(CUBES, *angles_for(angles, 3))
    assert qc.num_qubits == 24 and "measure" not in qc.count_ops()
    # Qiskit's own Statevector takes ~2 min on 24 qubits; Aer's exact statevector takes seconds
    exact = transpile(qc, basis_gates=["rz", "sx", "x", "cx"], seed_transpiler=7)
    exact.save_statevector()
    psi = np.asarray(AerSimulator(method="statevector").run(exact).result().get_statevector())
    probs = np.abs(psi) ** 2
    index = np.arange(2 ** 24)
    inside = np.ones(2 ** 24, dtype=bool)
    for t in range(8):
        inside &= np.bitwise_count((index >> (3 * t)) & 7) == 1
    assert 1 - probs[inside].sum() < 1e-10
    assert sum(probs[int(k, 2)] for k in KNOWN_KEYS) == pytest.approx(0.0518, abs=1e-3)
