"""Starter encoding (one-hot, 3 qubits per pick): Hamiltonians, the warm-up QAOA, one-hot QAOA and decoders."""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.circuit.library import RYGate, XGate, XXPlusYYGate
from qiskit.quantum_info import SparsePauliOp, Statevector
from scipy.optimize import minimize

from src.puzzle import CUBES, LAMBDA, MU, diagonal, front_back_picks, letters_of, solution_strings


def var(q, n):
    """The 0/1 variable on qubit q of n qubits, as (1 - Z_q) / 2."""
    return SparsePauliOp.from_sparse_list([("", [], 0.5), ("Z", [q], -0.5)], n)


def build_hamiltonian(cubes, lam=LAMBDA, mu=MU, colours=None):
    """Starter full-tower Hamiltonian on 6N qubits: x[c][p] on qubit 6c+p, y[c][p] on 6c+3+p."""
    colours = colours or letters_of(cubes)
    n = 6 * len(cubes)
    one = SparsePauliOp("I" * n)
    xs = [[var(6 * c + p, n) for p in range(3)] for c in range(len(cubes))]
    ys = [[var(6 * c + 3 + p, n) for p in range(3)] for c in range(len(cubes))]
    H = 0 * one
    for c in range(len(cubes)):
        for row in (xs[c], ys[c]):
            pick = sum(row, -1 * one)
            H += lam * (pick @ pick)
        H += mu * sum(xs[c][p] @ ys[c][p] for p in range(3))
    for picks in (xs, ys):
        for k in colours:
            d = -2 * one
            for c, cube in enumerate(cubes):
                for p in range(3):
                    if cube[p].count(k):
                        d += cube[p].count(k) * picks[c][p]
            H += d @ d
    return H.simplify()


def front_back_hamiltonian(cubes, lam=0, colours=None):
    """Degree rule on the x variables only (3N qubits); lam adds the one-pair-per-cube penalty."""
    colours = colours or letters_of(cubes)
    n = 3 * len(cubes)
    one = SparsePauliOp("I" * n)
    H = 0 * one
    for k in colours:
        d = -2 * one
        for c, cube in enumerate(cubes):
            for p in range(3):
                d += cube[p].count(k) * var(3 * c + p, n)
        H += d @ d
    for c in range(len(cubes)):
        pick = sum((var(3 * c + p, n) for p in range(3)), -1 * one)
        H += lam * (pick @ pick)
    return H.simplify()


def energy(H, bits):
    """Value of a Z-only Hamiltonian on a bitstring; bits[q] is qubit q."""
    total = 0.0
    for label, coeff in zip(H.paulis.to_labels(), H.coeffs):
        sign = 1
        for q, op in enumerate(reversed(label)):  # Qiskit labels put qubit 0 last
            if op == "Z" and bits[q]:
                sign = -sign
        total += coeff.real * sign
    return total


def to_bits(x, y):
    """Flatten x, y into the 6N-qubit layout: cube c gives x[c] then y[c]."""
    bits = []
    for c in range(len(x)):
        bits += x[c] + y[c]
    return bits


def cost_layer(qc, H, gamma):
    """exp(-i gamma H) for a Z-only Hamiltonian; terms with 3 or more Z use a CX ladder around one rz."""
    for label, coeff in zip(H.paulis.to_labels(), H.coeffs):
        qubits = [q for q, op in enumerate(reversed(label)) if op == "Z"]
        angle = 2 * gamma * coeff.real
        if len(qubits) == 1:
            qc.rz(angle, qubits[0])
        elif len(qubits) == 2:
            qc.rzz(angle, *qubits)
        elif len(qubits) >= 3:
            ladder = list(zip(qubits[:-1], qubits[1:]))
            for a, b in ladder:
                qc.cx(a, b)            # parity of all the qubits lands on the last one
            qc.rz(angle, qubits[-1])
            for a, b in reversed(ladder):
                qc.cx(a, b)
        # the identity term is a global phase and is skipped


# ---------------------------------------------------------------- warm-up: front/back only (starter verbatim)

def w_state(qc, a, b, c):
    """Equal spread over |100>, |010>, |001> on qubits a, b, c."""
    qc.ry(2 * np.arcsin(1 / np.sqrt(3)), a)
    qc.append(RYGate(np.pi / 2).control(1, ctrl_state=0), [a, b])
    qc.append(XGate().control(2, ctrl_state="00"), [a, b, c])


def xy_mixer(qc, beta, cubes):
    """XY mixer on each triple 3c, 3c+1, 3c+2: moves the single 1 around, never adds or removes one."""
    for c in range(len(cubes)):
        q = [3 * c, 3 * c + 1, 3 * c + 2]
        for i, j in ((0, 1), (0, 2), (1, 2)):
            qc.append(XXPlusYYGate(2 * beta), [q[i], q[j]])


def constrained_qaoa(H, gammas, betas, cubes=CUBES):
    """Starter warm-up QAOA: one W state per cube, then cost layer and XY mixer per round."""
    qc = QuantumCircuit(3 * len(cubes))
    for c in range(len(cubes)):
        w_state(qc, 3 * c, 3 * c + 1, 3 * c + 2)
    for g, b in zip(gammas, betas):
        qc.barrier(label="cost")
        cost_layer(qc, H, g)
        qc.barrier(label="mixer")
        xy_mixer(qc, b, cubes)
    return qc


def good_strings(cubes):
    """Qiskit-order bitstrings of every good front/back pick."""
    return solution_strings(front_back_picks(cubes))


def scan(H, gammas, betas, good, cubes=CUBES):
    """Average cost and success probability of p = 1 warm-up QAOA over a grid of angles (Statevector)."""
    g, b = Parameter("g"), Parameter("b")
    template = constrained_qaoa(H, [g], [b], cubes)
    costs, wins = diagonal(H), [int(s, 2) for s in good]
    avg = np.zeros((len(gammas), len(betas)))
    hit = np.zeros_like(avg)
    for i, gv in enumerate(gammas):
        for j, bv in enumerate(betas):
            probs = Statevector(template.assign_parameters({g: gv, b: bv})).probabilities()
            avg[i, j], hit[i, j] = probs @ costs, probs[wins].sum()
    return avg, hit


def optimise_warmup(H, start, cubes=CUBES, maxiter=200):
    """COBYLA on the average cost; start = [gammas..., betas...]. Returns (best angles, cost history)."""
    costs = diagonal(H)
    history = []

    def average_cost(angles):
        p = len(angles) // 2
        probs = Statevector(constrained_qaoa(H, angles[:p], angles[p:], cubes)).probabilities()
        history.append(float(probs @ costs))
        return history[-1]

    result = minimize(average_cost, start, method="COBYLA", options={"maxiter": maxiter})
    return result.x, history


# ---------------------------------------------------------------- starter encoding, full tower

def onehot_qaoa(cubes, gammas, betas, H=None):
    """One-hot QAOA on 6N qubits: a W state on both triples of every cube, cost layer, XY mixer on both."""
    n = len(cubes)
    H = build_hamiltonian(cubes, lam=0, mu=2) if H is None else H
    qc = QuantumCircuit(6 * n)
    for t in range(2 * n):                     # triple t is qubits 3t, 3t+1, 3t+2 (x then y per cube)
        w_state(qc, 3 * t, 3 * t + 1, 3 * t + 2)
    for g, b in zip(gammas, betas):
        cost_layer(qc, H, g)
        xy_mixer(qc, b, range(2 * n))          # the same XY mixer, on all 2N triples
    return qc


def _one_hot_index(bits):
    """The position of the single 1 in a triple, or None."""
    return bits.index(1) if sum(bits) == 1 else None


def decode_onehot(key, n):
    """(front/back, left/right) pick per cube from a 6N-qubit key; None if a triple is not one-hot or fb == lr."""
    bits = [int(ch) for ch in key.replace(" ", "")[-6 * n:][::-1]]   # bits[q] = qubit q
    choice = []
    for c in range(n):
        fb = _one_hot_index(bits[6 * c:6 * c + 3])
        lr = _one_hot_index(bits[6 * c + 3:6 * c + 6])
        if fb is None or lr is None or fb == lr:
            return None
        choice.append((fb, lr))
    return choice


def decode_frontback(key, n):
    """Front/back pick per cube from a 3N-qubit key; None if a triple is not one-hot."""
    bits = [int(ch) for ch in key.replace(" ", "")[-3 * n:][::-1]]
    picks = [_one_hot_index(bits[3 * c:3 * c + 3]) for c in range(n)]
    return None if None in picks else picks
