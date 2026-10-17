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


STARTER = REPO / "starter_notebook.ipynb"
STARTER_NAMES = ("orientations", "solves", "make_puzzle", "count_answers")


def load_starter(names=STARTER_NAMES):
    """Exec only the named function definitions from the challenge's starter notebook,
    so the bonus puzzle and its answer counter are the challenge's own code."""
    import ast
    import json
    import random

    module = ast.Module(body=[], type_ignores=[])
    for cell in json.loads(STARTER.read_text(encoding="utf-8"))["cells"]:
        if cell["cell_type"] == "code":
            tree = ast.parse("".join(cell["source"]))
            module.body += [node for node in tree.body
                            if isinstance(node, ast.FunctionDef) and node.name in names]
    namespace = {"itertools": itertools, "random": random, "CHOICES": CHOICES}
    exec(compile(module, str(STARTER), "exec"), namespace)
    return {name: namespace[name] for name in names}


def starter_puzzle(n, seed):
    return load_starter()["make_puzzle"](n, seed)


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


def one_hot_decomposition(cubes):
    """Exact split of the legal cost into one- and two-cube tables, read off the cost
    tensor with reference pick r = (0, ..., 0):
        cost(k) = cost(r) + sum_c a[c][k_c] + sum_{c<d} B[c, d][k_c, k_d].
    It is exact because the degree cost is a sum of squares of terms linear in the
    picks, so it has no three-cube terms (checked by brute force in the tests)."""
    costs = cost_tensor(cubes)
    n = costs.ndim

    def at(picks):  # cost with cube c at choice picks[c], every other cube at choice 0
        index = [0] * n
        for c, k in picks.items():
            index[c] = k
        return costs[tuple(index)]

    base = at({})
    single = [np.array([at({c: k}) - base for k in range(6)]) for c in range(n)]
    pair = {}
    for c, d in itertools.combinations(range(n), 2):
        pair[c, d] = np.array([[at({c: k, d: l}) - base
                                - single[c][k] - single[d][l]
                                for l in range(6)] for k in range(6)])
    return base, single, pair


def best_gauge(table):
    """Re-reference one pair table: B'[k,l] = B[k,l] - B[k,l0] - B[k0,l] + B[k0,l0],
    with (k0, l0) chosen to leave the fewest non-zero entries. Returns B', u, v with
    B = B' + u[k] + v[l]; on one-hot states u and v are free single-cube terms."""
    best = None
    for k0, l0 in itertools.product(range(6), repeat=2):
        u = table[:, l0].copy()
        v = table[k0, :] - table[k0, l0]
        reduced = table - u[:, None] - v[None, :]
        nonzero = int(np.sum(np.abs(reduced) > 1e-12))
        if best is None or nonzero < best[0]:
            best = (nonzero, reduced, u, v)
    return best[1], best[2], best[3]


def qubo_to_pauli(const, linear, quadratic, n_qubits):
    """Z/ZZ Hamiltonian of const + sum h_q x_q + sum J_qr x_q x_r with x = (1 - Z) / 2."""
    terms = {(): const}

    def add(key, value):
        terms[key] = terms.get(key, 0.0) + value

    for q, h in linear.items():
        add((), h / 2)
        add((q,), -h / 2)
    for (q, r), j in quadratic.items():
        add((), j / 4)
        add((q,), -j / 4)
        add((r,), -j / 4)
        add((q, r), j / 4)
    sparse = [("Z" * len(key), list(key), value) for key, value in terms.items()
              if abs(value) > 1e-12]
    return SparsePauliOp.from_sparse_list(sparse, n_qubits)


def reduced_hamiltonian(cubes, gauge="reference0"):
    """Hamiltonian that equals cost_tensor on every one-hot bitstring, without the
    terms that are constant there (intra-cube ZZ, and pair-table rows/columns that
    the one-hot rule turns into single-qubit terms).
    gauge="reference0": measure each pair table relative to choice 0 (Lesson 1).
    gauge="best": per cube pair, the reference row/column with the fewest non-zeros."""
    base, single, pair = one_hot_decomposition(cubes)
    linear = {6 * c + k: single[c][k] for c in range(len(cubes)) for k in range(6)}
    quadratic = {}
    for (c, d), table in pair.items():
        if gauge == "best":
            table, u, v = best_gauge(table)
            for k in range(6):
                linear[6 * c + k] += u[k]
                linear[6 * d + k] += v[k]
        for k, l in zip(*np.nonzero(np.abs(table) > 1e-12)):
            quadratic[6 * c + k, 6 * d + l] = table[k, l]
    return qubo_to_pauli(base, linear, quadratic, 6 * len(cubes)).simplify(atol=1e-12)


def term_counts(H):
    weights = [label.count("Z") for label in H.paulis.to_labels()]
    return {"terms": len(weights), "Z": weights.count(1), "ZZ": weights.count(2)}


# ---------------------------------------------------------------- subspace simulator

RING_PAIRS = [(i, (i + 1) % 6) for i in range(6)]
MIXERS = {"full": MIX_PAIRS, "ring": RING_PAIRS}


def xy_one_hot(beta, pairs=MIX_PAIRS):
    """The per-cube XY mixer (XXPlusYY(2 beta) on `pairs`, in order) restricted to the
    6 one-hot states, read off Qiskit's own gate matrices. Same construction as the
    notebook, so COBYLA follows the identical path (the closed form below differs
    by ~1e-16, which shifts COBYLA's result)."""
    qc = QuantumCircuit(6)
    for i, j in pairs:
        qc.append(XXPlusYYGate(2 * beta), [i, j])
    keep = [1 << k for k in range(6)]
    return Operator(qc).data[np.ix_(keep, keep)]


def xy_one_hot_fast(beta, pairs=MIX_PAIRS):
    """Closed form of xy_one_hot. Each gate is the 2x2 rotation
    [[cos b, -i sin b], [-i sin b, cos b]] on the states |k=i> and |k=j>."""
    c, s = np.cos(beta), np.sin(beta)
    U = np.eye(6, dtype=complex)
    for i, j in pairs:
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


def qaoa_state(costs, gammas, betas, pairs=MIX_PAIRS):
    """Exact QAOA state on the legal subspace, starting from the product of W states."""
    n = costs.ndim
    psi = np.full((6,) * n, 6 ** (-n / 2), dtype=complex)
    for gamma, beta in zip(gammas, betas):
        psi = psi * np.exp(-1j * gamma * costs)
        psi = apply_mixer(psi, xy_one_hot(beta, pairs))
    return psi


def average_and_hit(psi, costs, solved):
    probs = np.abs(psi) ** 2
    return float(np.sum(probs * costs)), float(probs[solved].sum())


# ---------------------------------------------------------------- training objectives
# Each maps (probabilities, costs) to a number to minimize. P(solved) is always the score;
# the objective is only the training signal, and none of them uses the solved set.

def objective_average(probs, costs):
    return float(np.sum(probs * costs))


def objective_cvar(probs, costs, alpha=0.1):
    """Mean cost of the lowest-cost alpha fraction of the probability mass."""
    order = np.argsort(costs, axis=None)
    p, c = probs.ravel()[order], costs.ravel()[order]
    before = np.cumsum(p) - p
    take = np.clip(alpha - before, 0, p)
    return float(np.sum(take * c) / alpha)


def objective_gibbs(probs, costs, eta=1.0):
    """-log E[exp(-eta C)]: low costs dominate the sum, so moving weight to cost 0
    counts far more than moving it from 10 to 4. Uses only the costs."""
    return float(-np.log(np.sum(probs * np.exp(-eta * costs))))


def cost_histogram(counts, cubes):
    """{cost: shots} from measured Qiskit counts. Only each bitstring's cost is kept;
    shots that are not one-hot have no legal cost and are left out."""
    costs = cost_tensor(cubes)
    hist = {}
    for bits, shots in counts.items():
        choice = decode(bits, len(cubes))
        if choice is not None:
            cost = float(costs[tuple(choice)])
            hist[cost] = hist.get(cost, 0) + shots
    return hist


def gibbs_from_histogram(hist, eta=1.0):
    """The Gibbs objective computed from a {cost: weight} histogram (shots or probabilities)."""
    total = sum(hist.values())
    return float(-np.log(sum(w * np.exp(-eta * c) for c, w in hist.items()) / total))


OBJECTIVES = {"average": objective_average, "cvar0.1": objective_cvar,
              "gibbs1": objective_gibbs}


# ---------------------------------------------------------------- angle training (notebook recipe)

def grid_p1(costs, solved, points=25, pairs=MIX_PAIRS):
    """p=1 grid on [0, pi]^2 (one gamma period, costs are even integers);
    returns the (gamma, beta) with the lowest average cost."""
    grid = np.linspace(0, np.pi, points)
    best = None
    for gamma in grid:
        for beta in grid:
            state = qaoa_state(costs, [gamma], [beta], pairs)
            avg, _ = average_and_hit(state, costs, solved)
            if best is None or avg < best[0]:
                best = (avg, float(gamma), float(beta))
    return best[1], best[2]


def train_fixed_p(costs, p, x0, maxiter, pairs=MIX_PAIRS, objective=objective_average):
    """COBYLA on `objective` for fixed depth p; x = gammas + betas."""
    def loss(x):
        return objective(np.abs(qaoa_state(costs, x[:p], x[p:], pairs)) ** 2, costs)

    result = minimize(loss, np.asarray(x0, dtype=float), method="COBYLA",
                      options={"maxiter": maxiter, "rhobeg": 0.35})
    return result.x


def train_layerwise(costs, solved, p_max=7, pairs=MIX_PAIRS, objective=objective_average,
                    jitter_seed=None, jitter=0.05, start=None):
    """Notebook recipe: p=1 grid, then grow one layer at a time, repeating the last angles.
    `start` reuses a precomputed grid_p1 result. With jitter_seed set, N(0, jitter)
    noise is added to the p=1 start angles."""
    layers = train_layers(costs, solved, p_max, pairs, objective, jitter_seed, jitter, start)
    curve = [(p, avg, hit) for p, _, avg, hit in layers]
    return layers[-1][1], curve


def train_layers(costs, solved, p_max=7, pairs=MIX_PAIRS, objective=objective_average,
                 jitter_seed=None, jitter=0.05, start=None):
    """Same training as train_layerwise, but returns (p, angles, avg, P(solved)) for every
    p on the way to p_max, so a depth sweep needs no retraining."""
    start = np.array(start if start is not None else grid_p1(costs, solved, pairs=pairs))
    if jitter_seed is not None:
        start = start + np.random.default_rng(jitter_seed).normal(0, jitter, 2)
    angles = train_fixed_p(costs, 1, start, 80, pairs, objective)
    layers = [(1, angles, *average_and_hit(qaoa_state(costs, angles[:1], angles[1:], pairs),
                                           costs, solved))]
    for p in range(2, p_max + 1):
        g, b = angles[: p - 1], angles[p - 1:]
        x0 = np.concatenate([g, [g[-1]], b, [b[-1]]])
        angles = train_fixed_p(costs, p, x0, 220 if p < 5 else 400, pairs, objective)
        state = qaoa_state(costs, angles[:p], angles[p:], pairs)
        layers.append((p, angles, *average_and_hit(state, costs, solved)))
    return layers


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


def tower_qaoa(cubes, hamiltonian, gammas, betas, pairs=MIX_PAIRS):
    qc = QuantumCircuit(6 * len(cubes))
    for c in range(len(cubes)):
        w_state(qc, list(range(6 * c, 6 * c + 6)))
    for gamma, beta in zip(gammas, betas):
        cost_layer(qc, hamiltonian, gamma)
        for c in range(len(cubes)):
            for i, j in pairs:
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


def one_hot_index(choice_indices):
    """Statevector index of a legal pick (qubit 6c + k set for each cube c)."""
    return sum(1 << (6 * c + k) for c, k in enumerate(choice_indices))


def one_hot_probabilities(statevector_probs, n_cubes):
    """Pull the 6^N one-hot probabilities out of a full 2^(6N) probability vector,
    as a tensor indexed like qaoa_state. Also returns the mass outside one-hot."""
    out = np.zeros((6,) * n_cubes)
    for index in itertools.product(range(6), repeat=n_cubes):
        out[index] = statevector_probs[one_hot_index(index)]
    return out, float(statevector_probs.sum() - out.sum())


# ---------------------------------------------------------------- metrics

def transpile_metrics(circuit, optimization_level=1):
    """optimization_level=None is the GRADING call: transpile(qc, basis_gates=BASIS)."""
    if optimization_level is None:
        compiled = transpile(circuit, basis_gates=BASIS)
    else:
        compiled = transpile(circuit, basis_gates=BASIS, optimization_level=optimization_level,
                             seed_transpiler=SEED)
    level = "default" if optimization_level is None else optimization_level
    return compiled, {"qubits": compiled.num_qubits, "depth": compiled.depth(),
                      "cx": compiled.count_ops().get("cx", 0), "optimization_level": level}


def aer_counts(compiled, shots=1000, seed=SEED):
    qc = compiled.copy()
    qc.measure_all()
    sim = AerSimulator(method="statevector", seed_simulator=seed)
    return sim.run(qc, shots=shots).result().get_counts()


def aer_exact_p_solved(compiled, mask):
    """P(solved) and mass outside one-hot from the full Aer statevector of a
    transpiled circuit (Aer does not know XXPlusYYGate)."""
    qc = compiled.copy()
    qc.save_statevector()
    sim = AerSimulator(method="statevector", seed_simulator=SEED)
    data = np.asarray(sim.run(qc).result().get_statevector())
    probs, outside = one_hot_probabilities(np.abs(data) ** 2, mask.ndim)
    return float(probs[mask].sum()), outside


CX_ERROR, ONE_QUBIT_ERROR, READOUT_ERROR = 1e-2, 5e-4, 0.02


def noise_model(cx_error=CX_ERROR, one_qubit_error=ONE_QUBIT_ERROR, readout=READOUT_ERROR):
    """Stated assumptions, not a device: depolarizing on cx and on sx/x, none on rz
    (a virtual frame change), symmetric readout flips on every qubit."""
    from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

    model = NoiseModel(basis_gates=BASIS)
    model.add_all_qubit_quantum_error(depolarizing_error(cx_error, 2), ["cx"])
    model.add_all_qubit_quantum_error(depolarizing_error(one_qubit_error, 1), ["sx", "x"])
    model.add_all_qubit_readout_error(
        ReadoutError([[1 - readout, readout], [readout, 1 - readout]]))
    return model


def noisy_counts(compiled, model=None, shots=2000, seed=SEED):
    """Counts from the transpiled circuit, with or without a noise model."""
    qc = compiled.copy()
    qc.measure_all()
    sim = AerSimulator(method="statevector", seed_simulator=seed, noise_model=model)
    return sim.run(qc, shots=shots).result().get_counts()


def rates_from_counts(counts, cubes):
    """All shot rates from raw counts. Solved shots are checked with solves();
    post-selection keeps exactly the shots that decode as one-hot."""
    m = shot_metrics(counts, cubes)
    return {"shots": m["shots"], "one_hot": m["valid"], "solved": m["solved"],
            "post_selected_shots": m["valid"], "p_solved": m["solved"] / m["shots"],
            "one_hot_fraction": m["valid"] / m["shots"],
            "p_post_selected": m["solved"] / m["valid"] if m["valid"] else 0.0}


# ---------------------------------------------------------------- hardware file and readout

def hardware_circuit(cubes, angles, gauge="best"):
    """The circuit submit_job would receive: the accepted recipe at the given angles,
    passed through resources.helpers.prepare (marker qubit at 1, measure all, transpile)."""
    from resources.helpers import prepare

    p = len(angles) // 2
    H = reduced_hamiltonian(cubes, gauge)
    return prepare(tower_qaoa(cubes, H, angles[:p], angles[p:], MIX_PAIRS))


def qasm_text(circuit):
    from qiskit import qasm2

    return qasm2.dumps(circuit)


def load_qasm(path):
    from qiskit import qasm2

    # qelib1.inc has no sx; the legacy list teaches the parser the gates dumps() writes.
    return qasm2.loads(Path(path).read_text(),
                       custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)


def run_loaded(circuit, shots=2000, seed=SEED, model=None):
    """Aer counts for a circuit that already measures every qubit."""
    sim = AerSimulator(method="statevector", seed_simulator=seed, noise_model=model)
    return sim.run(circuit, shots=shots).result().get_counts()


MARKER_MIN = 0.9   # the marker end must read 1 in at least this fraction of shots


def split_marker(raw):
    """Like helpers.strip_marker, but a shot whose marker reads 0 (readout noise) is dropped
    and counted instead of raising. The marker end is the end that reads 1 in at least
    MARKER_MIN of the shots; if both ends (or neither) do, qubit 0 could be mistaken for the
    marker, so this raises instead of guessing."""
    total = sum(raw.values())
    left = sum(n for k, n in raw.items() if k[0] == "1") / total
    right = sum(n for k, n in raw.items() if k[-1] == "1") / total
    if left >= MARKER_MIN > right:
        kept = {k[1:]: n for k, n in raw.items() if k[0] == "1"}
    elif right >= MARKER_MIN > left:
        kept = {k[:-1][::-1]: n for k, n in raw.items() if k[-1] == "1"}
    else:
        raise ValueError(f"marker end is ambiguous (left {left:.2f}, right {right:.2f})")
    return kept, total - sum(kept.values())


def results_row(counts, cubes, marker=False, **table):
    """Counts -> results-table fields. P(correct tower) over all shots and post-selected on
    one-hot shots; every solved shot is checked with solves()."""
    dropped = 0
    if marker:
        counts, dropped = split_marker(counts)
    m = shot_metrics(counts, cubes)
    return {**table, "total": m["shots"], "kept": m["valid"], "solved": m["solved"],
            "marker_dropped": dropped, "p_all": m["solved"] / m["shots"],
            "p_post_selected": m["solved"] / m["valid"] if m["valid"] else 0.0}


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
