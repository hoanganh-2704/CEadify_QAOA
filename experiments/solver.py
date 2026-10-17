"""Importable version of the constrained-QAOA model in solution.ipynb.

Encoding: 6 qubits per cube, one-hot over the 6 legal (front/back, left/right)
choices in CHOICES. Qubit 6c + k is "cube c uses choice k".

Two simulators of the same algorithm live here:
  * qaoa_state: fast, exact, works on the 6^N legal subspace (used for tuning);
  * tower_qaoa: the real Qiskit circuit (used for transpiling and Aer sampling).
experiments/tests_quantum.py checks that they agree.
"""
import itertools
import sys
from pathlib import Path

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import XXPlusYYGate
from qiskit.quantum_info import Operator, SparsePauliOp
from qiskit_aer import AerSimulator
from scipy.optimize import minimize

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from resources.helpers import SEED, tower_from  # noqa: E402

CUBES = [
    ["GR", "BR", "GY"],
    ["GY", "RB", "BY"],
    ["BR", "RG", "RY"],
    ["YR", "RG", "BG"],
]
CHOICES = list(itertools.permutations(range(3), 2))
MIX_PAIRS = list(itertools.combinations(range(6), 2))
BASIS = ["rz", "sx", "x", "cx"]


# ---------------------------------------------------------------- classical model

def colours_of(cubes):
    return sorted({ch for cube in cubes for pair in cube for ch in pair})


def cost_tensor(cubes):
    """Cost of every legal assignment; entry [k0, k1, ...] is cube c using choice k_c.

    Cost = sum over both axes and every colour of (degree - 2)^2, zero exactly
    when both axes are 2-factors (a solved tower).
    """
    n = len(cubes)
    total = np.zeros((6,) * n)
    for axis in (0, 1):
        for colour in colours_of(cubes):
            degree = np.zeros((6,) * n)
            for c, cube in enumerate(cubes):
                weights = [cube[CHOICES[k][axis]].count(colour) for k in range(6)]
                shape = [1] * n
                shape[c] = 6
                degree = degree + np.reshape(weights, shape)
            total += (degree - 2) ** 2
    return total


def solves(tower):
    """Independent four-sides check: every side shows len(tower) distinct colours."""
    return all(len({view[side] for view in tower}) == len(tower) for side in range(4))


def tower_of(cubes, choice_indices):
    return tower_from(cubes, [CHOICES[k] for k in choice_indices])


def solved_mask(cubes):
    """Boolean tensor of solved towers, built with solves(), not with the cost."""
    n = len(cubes)
    mask = np.zeros((6,) * n, dtype=bool)
    for index in itertools.product(range(6), repeat=n):
        mask[index] = solves(tower_of(cubes, index))
    return mask


def random_baselines(mask):
    """Chance that a uniform random legal pick / random 6N-bit string is solved."""
    n = mask.ndim
    hits = int(mask.sum())
    return {"random_legal": hits / 6 ** n, "random_bits": hits / 2 ** (6 * n)}


# ---------------------------------------------------------------- Hamiltonian

def choice_hamiltonian(cubes):
    """Z/ZZ Hamiltonian equal to cost_tensor on every one-hot bitstring."""
    n = 6 * len(cubes)
    one = SparsePauliOp("I" * n)

    def var(q):  # (1 - Z_q) / 2, the 0/1 value of qubit q
        return SparsePauliOp.from_sparse_list([("", [], 0.5), ("Z", [q], -0.5)], n)

    H = 0 * one
    for axis in (0, 1):
        for colour in colours_of(cubes):
            degree = -2 * one
            for c, cube in enumerate(cubes):
                for k in range(6):
                    mult = cube[CHOICES[k][axis]].count(colour)
                    if mult:
                        degree += mult * var(6 * c + k)
            H += degree @ degree
    return H.simplify()


def energy(H, bits):
    """Value of a Z-only Hamiltonian; bits[q] is qubit q (Qiskit labels hold qubit 0 last)."""
    total = 0.0
    for label, coeff in zip(H.paulis.to_labels(), H.coeffs):
        sign = 1
        for q, op in enumerate(reversed(label)):
            if op == "Z" and bits[q]:
                sign = -sign
        total += float(coeff.real) * sign
    return total


# ---------------------------------------------------------------- subspace simulator

def xy_one_hot(beta):
    """The per-cube XY mixer (XXPlusYY(2 beta) on all 15 pairs, in MIX_PAIRS order)
    restricted to the 6 one-hot states, read off Qiskit's own gate matrices.
    Same construction as the notebook, so COBYLA follows the identical path
    (the closed form below differs by ~1e-16, which shifts COBYLA's result)."""
    qc = QuantumCircuit(6)
    for i, j in MIX_PAIRS:
        qc.append(XXPlusYYGate(2 * beta), [i, j])
    keep = [1 << k for k in range(6)]
    return Operator(qc).data[np.ix_(keep, keep)]


def xy_one_hot_fast(beta):
    """The per-cube XY mixer (XXPlusYY(2 beta) on all 15 pairs, in MIX_PAIRS order)
    restricted to the 6 one-hot states, closed form. Each gate is a 2x2 rotation
    [[cos b, -i sin b], [-i sin b, cos b]] on the states |k=i> and |k=j>."""
    c, s = np.cos(beta), np.sin(beta)
    U = np.eye(6, dtype=complex)
    for i, j in MIX_PAIRS:
        G = np.eye(6, dtype=complex)
        G[i, i] = G[j, j] = c
        G[i, j] = G[j, i] = -1j * s
        U = G @ U
    return U


def apply_mixer(psi, unitary):
    """Apply the same 6x6 unitary to every cube axis of the state tensor."""
    for axis in range(psi.ndim):
        psi = np.moveaxis(np.moveaxis(psi, axis, -1) @ unitary.T, -1, axis)
    return psi


def qaoa_state(costs, gammas, betas):
    """Exact QAOA state on the legal subspace, starting from the product of W states."""
    n = costs.ndim
    psi = np.full((6,) * n, 6 ** (-n / 2), dtype=complex)
    for gamma, beta in zip(gammas, betas):
        psi = psi * np.exp(-1j * gamma * costs)
        psi = apply_mixer(psi, xy_one_hot(beta))
    return psi


def average_and_hit(psi, costs, solved):
    probs = np.abs(psi) ** 2
    return float(np.sum(probs * costs)), float(probs[solved].sum())


# ---------------------------------------------------------------- angle training (notebook recipe)

def grid_p1(costs, solved, points=25):
    """p=1 grid on [0, pi]^2; returns the (gamma, beta) with the lowest average cost."""
    grid = np.linspace(0, np.pi, points)
    best = None
    for gamma in grid:
        for beta in grid:
            avg, _ = average_and_hit(qaoa_state(costs, [gamma], [beta]), costs, solved)
            if best is None or avg < best[0]:
                best = (avg, float(gamma), float(beta))
    return best[1], best[2]


def train_average(costs, solved, p, x0, maxiter):
    """COBYLA on the average cost for fixed depth p; x = gammas + betas."""
    def objective(x):
        return average_and_hit(qaoa_state(costs, x[:p], x[p:]), costs, solved)[0]

    result = minimize(objective, np.asarray(x0, dtype=float), method="COBYLA",
                      options={"maxiter": maxiter, "rhobeg": 0.35})
    return result.x


def train_layerwise(costs, solved, p_max=7):
    """Notebook recipe: p=1 grid, then grow one layer at a time, repeating the last angles."""
    angles = train_average(costs, solved, 1, grid_p1(costs, solved), maxiter=80)
    curve = [(1, *average_and_hit(qaoa_state(costs, angles[:1], angles[1:]), costs, solved))]
    for p in range(2, p_max + 1):
        g, b = angles[: p - 1], angles[p - 1:]
        start = np.concatenate([g, [g[-1]], b, [b[-1]]])
        angles = train_average(costs, solved, p, start, maxiter=220 if p < 5 else 400)
        state = qaoa_state(costs, angles[:p], angles[p:])
        curve.append((p, *average_and_hit(state, costs, solved)))
    return angles, curve


# ---------------------------------------------------------------- circuit

def w_state(qc, qubits):
    """Equal superposition of the single-1 bitstrings on `qubits`."""
    n = len(qubits)
    qc.x(qubits[0])
    for i in range(n - 1):
        qc.cry(2 * np.arccos(1 / np.sqrt(n - i)), qubits[i], qubits[i + 1])
        qc.cx(qubits[i + 1], qubits[i])


def cost_layer(qc, hamiltonian, gamma):
    """exp(-i gamma H) up to global phase, for Z and ZZ terms."""
    for label, coeff in zip(hamiltonian.paulis.to_labels(), hamiltonian.coeffs):
        qubits = [q for q, op in enumerate(reversed(label)) if op == "Z"]
        angle = 2 * float(gamma) * float(coeff.real)
        if len(qubits) == 1:
            qc.rz(angle, qubits[0])
        elif len(qubits) == 2:
            qc.rzz(angle, *qubits)
        elif len(qubits) > 2:
            raise ValueError("cost_layer only handles Z and ZZ terms")


def tower_qaoa(cubes, hamiltonian, gammas, betas):
    qc = QuantumCircuit(6 * len(cubes))
    for c in range(len(cubes)):
        w_state(qc, list(range(6 * c, 6 * c + 6)))
    for gamma, beta in zip(gammas, betas):
        cost_layer(qc, hamiltonian, gamma)
        for c in range(len(cubes)):
            for i, j in MIX_PAIRS:
                qc.append(XXPlusYYGate(2 * float(beta)), [6 * c + i, 6 * c + j])
    return qc


def decode(bitstring, n_cubes):
    """Qiskit counts key -> list of choice indices, or None if a cube block is not one-hot.
    Qubit 0 is the rightmost character."""
    bits = bitstring.replace(" ", "")[::-1]
    choices = []
    for c in range(n_cubes):
        block = bits[6 * c: 6 * c + 6]
        if block.count("1") != 1:
            return None
        choices.append(block.index("1"))
    return choices


def one_hot_probabilities(statevector_probs, n_cubes):
    """Pull the 6^N one-hot probabilities out of a full 2^(6N) probability vector,
    as a tensor indexed like qaoa_state. Also returns the mass outside one-hot."""
    out = np.zeros((6,) * n_cubes)
    for index in itertools.product(range(6), repeat=n_cubes):
        out[index] = statevector_probs[sum(1 << (6 * c + k) for c, k in enumerate(index))]
    return out, float(statevector_probs.sum() - out.sum())


# ---------------------------------------------------------------- metrics

def transpile_metrics(circuit, optimization_level=1):
    compiled = transpile(circuit, basis_gates=BASIS, optimization_level=optimization_level,
                         seed_transpiler=SEED)
    return compiled, {"qubits": compiled.num_qubits, "depth": compiled.depth(),
                      "cx": compiled.count_ops().get("cx", 0),
                      "optimization_level": optimization_level}


def aer_counts(compiled, shots=1000, seed=SEED):
    qc = compiled.copy()
    qc.measure_all()
    sim = AerSimulator(method="statevector", seed_simulator=seed)
    return sim.run(qc, shots=shots).result().get_counts()


def shot_metrics(counts, cubes):
    """Valid (one-hot) and solved shot counts, each solved tower checked with solves()."""
    shots = sum(counts.values())
    valid = solved = 0
    for bitstring, k in counts.items():
        choice = decode(bitstring, len(cubes))
        if choice is None:
            continue
        valid += k
        if solves(tower_of(cubes, choice)):
            solved += k
    return {"shots": shots, "valid": valid, "solved": solved, "p_solved": solved / shots}
