"""Compact encoding (3 qubits per cube), its Hamiltonian, the compact QAOA circuit and an exact simulator.

Cube c lives on qubits 3c, 3c+1, 3c+2 and stores a code k in 0..5 (little-endian), k = index into
CHOICES = (front/back pair, left/right pair). Codes 6 and 7 are invalid; the start state and the
per-cube mixer never reach them, and the Hamiltonian gives them a penalty so they are never zeros.
"""
import json
import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCPhaseGate, PauliEvolutionGate
from qiskit.quantum_info import SparsePauliOp
from scipy.optimize import minimize

from src.puzzle import CHOICES, SEED, cost_table, instance, letters_of, tower_from, verify_choice

LAM_INVALID = 4.0


# ---------------------------------------------------------------- keys, codes and choices

def codes_from_key(key, n):
    """Codes k_c of a Qiskit counts key (qubit 0 rightmost); only the rightmost 3n characters are read."""
    bits = key.replace(" ", "")[-3 * n:][::-1]   # bits[q] = value of qubit q
    return [int(bits[3 * c]) + 2 * int(bits[3 * c + 1]) + 4 * int(bits[3 * c + 2]) for c in range(n)]


def key_from_codes(codes, n_extra=0):
    """The Qiskit-order key of a list of codes, with n_extra leading '0' characters."""
    bits = []
    for k in codes:
        bits += [str((k >> i) & 1) for i in range(3)]
    return "0" * n_extra + "".join(reversed(bits))


def choice_from_codes(codes):
    """The (front/back, left/right) choice per cube, or None if any code is 6 or 7."""
    if any(k >= 6 for k in codes):
        return None
    return [CHOICES[k] for k in codes]


def decode_tower(cubes, key):
    """The tower of a counts key if it passes verify_choice, else None."""
    choice = choice_from_codes(codes_from_key(key, len(cubes)))
    if choice is None or not verify_choice(cubes, choice):
        return None
    return tower_from(cubes, choice)


# ---------------------------------------------------------------- the Hamiltonian

def walsh(fvals):
    """Walsh coefficients of f on 3 bits: f(x) = sum over subsets S of c_S * prod_{i in S} z_i, z = (-1)**x."""
    return {S: sum(fvals[x] * (-1) ** bin(S & x).count("1") for x in range(8)) / 8
            for S in range(8)}


def best_dont_care(fvals6):
    """Pick f(6), f(7) so the two highest-order Walsh terms (Z0Z1Z2 and Z1Z2) vanish."""
    A, rhs = [], []
    for S in (0b111, 0b110):
        base = sum(fvals6[x] * (-1) ** bin(S & x).count("1") for x in range(6)) / 8
        A.append([(-1) ** bin(S & 6).count("1") / 8, (-1) ** bin(S & 7).count("1") / 8])
        rhs.append(-base)
    return list(fvals6) + list(np.linalg.solve(np.array(A), np.array(rhs)))


def _z(qubits, coeff, nq):
    """The operator coeff * prod Z_q on nq qubits."""
    return SparsePauliOp.from_sparse_list([("Z" * len(qubits), qubits, coeff)], nq)


def compact_hamiltonian(cubes, lam_invalid=LAM_INVALID):
    """Degree cost on 3N qubits (Z-only, at most 4-local) plus lam_invalid on every invalid cube code."""
    n = len(cubes)
    nq = 3 * n
    one = SparsePauliOp("I" * nq)
    H = 0 * one
    for side in range(2):
        for ch in letters_of(cubes):
            d = -2 * one                     # degree of colour ch on this side, minus 2
            for c, cube in enumerate(cubes):
                f6 = [cube[CHOICES[k][side]].count(ch) for k in range(6)]
                if not any(f6):
                    continue
                for S, coeff in walsh(best_dont_care(f6)).items():
                    if abs(coeff) > 1e-12:
                        d += _z([3 * c + i for i in range(3) if (S >> i) & 1], coeff, nq)
            H += d @ d
    for c in range(n):                       # [b1 = b2 = 1] = (1 - Z1 - Z2 + Z1 Z2) / 4 marks codes 6, 7
        q1, q2 = 3 * c + 1, 3 * c + 2
        H += lam_invalid / 4 * (one - _z([q1], 1, nq) - _z([q2], 1, nq) + _z([q1, q2], 1, nq))
    return H.simplify(atol=1e-10)


def valid_indices(n):
    """Statevector indices of the 6**n valid codes, in the same order as cost_table."""
    index = np.arange(6 ** n)
    return sum(((index // 6 ** c) % 6) << (3 * c) for c in range(n))


def diagonal_at(H, indices):
    """Value of a Z-only Hamiltonian on the given basis-state indices (qubit q = bit q of the index)."""
    indices = np.asarray(indices, dtype=np.int64)
    values = np.zeros(len(indices))
    for label, coeff in zip(H.paulis.to_labels(), H.coeffs):
        mask = sum(1 << q for q, op in enumerate(reversed(label)) if op == "Z")
        parity = np.bitwise_count(indices & mask) & 1
        values += coeff.real * (1 - 2 * parity.astype(float))
    return values


def check_hamiltonian(cubes, H=None):
    """Compare H with the classical cost: on every valid code and, for up to 18 qubits, on every bitstring."""
    n = len(cubes)
    H = compact_hamiltonian(cubes) if H is None else H
    cost = cost_table(cubes)
    on_valid = diagonal_at(H, valid_indices(n))
    out = {
        "n_qubits": H.num_qubits,
        "n_terms": len(H),
        "max_locality": max(label.count("Z") for label in H.paulis.to_labels()),
        "max_gap_valid": float(np.abs(on_valid - cost).max()),
        "zeros_valid": int((np.abs(on_valid) < 1e-9).sum()),
        "min_nonzero": float(on_valid[np.abs(on_valid) > 1e-9].min()),
    }
    if 3 * n <= 18:
        everything = np.arange(2 ** (3 * n))
        values = diagonal_at(H, everything)
        invalid = np.zeros(len(everything), dtype=bool)
        for c in range(n):
            invalid |= ((everything >> (3 * c + 1)) & 3) == 3
        out["zeros_all"] = int((np.abs(values) < 1e-9).sum())
        out["min_invalid"] = float(values[invalid].min())
    return out


# ---------------------------------------------------------------- the circuit

def uniform6(qc, base):
    """Equal superposition of the 6 valid codes on qubits base, base+1, base+2."""
    qc.h(base)
    qc.ry(2 * math.asin(1 / math.sqrt(3)), base + 2)
    qc.cry(math.pi / 2, base + 2, base + 1, ctrl_state=0)


def cube_mixer(qc, beta, base):
    """exp(-i beta |u><u|) on one cube, |u> = uniform over its 6 codes (a per-cube Grover mixer)."""
    qs = [base, base + 1, base + 2]
    prep = QuantumCircuit(3)
    uniform6(prep, 0)
    qc.compose(prep.inverse(), qs, inplace=True)
    qc.x(qs)
    qc.append(MCPhaseGate(-beta, 2), qs)
    qc.x(qs)
    qc.compose(prep, qs, inplace=True)


def compact_qaoa(cubes, gammas, betas, H=None):
    """Compact QAOA on 3N qubits: uniform-6 start, then per layer exp(-i gamma H) and a mixer per cube."""
    n = len(cubes)
    H = compact_hamiltonian(cubes) if H is None else H
    qc = QuantumCircuit(3 * n)
    for c in range(n):
        uniform6(qc, 3 * c)
    for g, b in zip(gammas, betas):
        qc.append(PauliEvolutionGate(H, time=g), range(3 * n))
        for c in range(n):
            cube_mixer(qc, b, 3 * c)
    return qc


# ---------------------------------------------------------------- exact simulator on the 6^N valid codes

def apply_local(psi, U, n, d):
    """Apply the same d x d matrix U to every cube axis of the flat state psi (cube 0 fastest)."""
    t = psi.reshape((d,) * n, order="F")
    for ax in range(n):
        t = np.moveaxis(np.tensordot(U, t, axes=([1], [ax])), 0, ax)
    return t.reshape(-1, order="F")


class Reduced:
    """Exact compact-QAOA simulator on the 6**N valid codes (the circuit never leaves them)."""

    def __init__(self, cubes):
        """Store the cost of every valid code and which codes are answers."""
        self.n = len(cubes)
        self.cost = cost_table(cubes).astype(float)
        self.good = np.flatnonzero(self.cost == 0)
        self.u = np.full(6, 1 / math.sqrt(6))

    def state(self, gammas, betas):
        """Amplitudes over the valid codes after the QAOA layers."""
        psi = np.full(6 ** self.n, 6 ** (-self.n / 2), dtype=complex)
        for g, b in zip(gammas, betas):
            psi = psi * np.exp(-1j * g * self.cost)
            mixer = np.eye(6) + (np.exp(-1j * b) - 1) * np.outer(self.u, self.u)
            psi = apply_local(psi, mixer, self.n, 6)
        return psi

    def probs(self, gammas, betas):
        """Probability of every valid code, ordered like cost_table."""
        return np.abs(self.state(gammas, betas)) ** 2

    def P(self, gammas, betas):
        """Probability of measuring an answer."""
        return float(self.probs(gammas, betas)[self.good].sum())

    def energy(self, gammas, betas):
        """Expected cost."""
        return float(self.probs(gammas, betas) @ self.cost)


# ---------------------------------------------------------------- angles

def load_angles(path):
    """Read an angle file as {p: {"angles": [g..., b...], "P": float, "exp_cost": float}}."""
    with open(path) as f:
        raw = json.load(f)
    out = {}
    for key, entry in raw.items():
        if key.isdigit():
            entry = dict(entry)
            if "exp_cost" not in entry and "E" in entry:
                entry["exp_cost"] = entry["E"]
            out[int(key)] = entry
    return out


def angles_for(angles, p):
    """The (gammas, betas) lists for depth p."""
    x = list(angles[p]["angles"])
    return x[:p], x[p:]


def ramp_angles(dg, db, p):
    """Linear ramp: gamma_i = dg * s_i, beta_i = db * (1 - s_i), s_i = (i + 0.5) / p."""
    s = (np.arange(p) + 0.5) / p
    return list(dg * s), list(db * (1 - s))


def transfer_table(angles, ns=(3, 4, 5, 6, 7, 8), ps=(8, 16, 24)):
    """Exact P on instance(n) with the same fixed angles, for every n in ns and p in ps."""
    out = {}
    for n in ns:
        sim = Reduced(instance(n))
        out[n] = {p: sim.P(*angles_for(angles, p)) for p in ps}
    return out


def _cvar(probs, cost, order, alpha):
    """Mean cost of the lowest-cost alpha fraction of the distribution."""
    ps = probs[order]
    weights = np.clip(alpha - (np.cumsum(ps) - ps), 0, ps)
    return float((weights * cost[order]).sum() / alpha)


def _options(objective, method, p):
    """Optimiser iteration limits used when the angle files were made."""
    if objective == "energy":
        return {} if p == 1 else {"maxiter": 500}
    return {"maxiter": 3000 if method == "Nelder-Mead" else 1500}


def train_layerwise(cubes, pmax, objective="energy", seed=SEED, log=print):
    """Train angles one depth at a time (grid for p = 1, then INTERP warm starts and L-BFGS-B).

    objective "energy" minimises E[cost]; "cvar_ladder" minimises CVaR with alpha = clip(2 P, 0.25, 1)
    and also tries Nelder-Mead and COBYLA. The method is deterministic; seed is kept for the interface.
    """
    sim = Reduced(cubes)
    order = np.argsort(sim.cost)
    methods = ("L-BFGS-B",) if objective == "energy" else ("Nelder-Mead", "COBYLA", "L-BFGS-B")
    if objective not in ("energy", "cvar_ladder"):
        raise ValueError(f"unknown objective {objective!r}")

    def split(x):
        p = len(x) // 2
        return x[:p], x[p:]

    out, x, P_prev = {}, None, 0.0
    for p in range(1, pmax + 1):
        alpha = 1.0 if objective == "energy" else float(np.clip(2 * P_prev, 0.25, 1.0))
        if objective == "energy":
            f = lambda y: sim.energy(*split(y))
        else:
            f = lambda y: _cvar(sim.probs(*split(y)), sim.cost, order, alpha)
        if p == 1:
            gs = np.linspace(0, np.pi, 24, endpoint=False)
            bs = np.linspace(0, 2 * np.pi, 24, endpoint=False)
            grid = np.array([[f(np.array([g, b])) for b in bs] for g in gs])
            i, j = np.unravel_index(grid.argmin(), grid.shape)
            starts = [np.array([gs[i], bs[j]])]
        else:
            interp = lambda v: np.interp(np.linspace(0, 1, p), np.linspace(0, 1, p - 1), v)
            starts = [np.concatenate([interp(x[:p - 1]), interp(x[p - 1:])]),
                      np.concatenate([x[:p - 1], [x[p - 2]], x[p - 1:], [x[-1]]])]
        best = None
        for start in starts:
            for method in methods:
                r = minimize(f, start, method=method, options=_options(objective, method, p))
                if best is None or r.fun < best.fun:
                    best = r
        x = best.x
        P_prev = sim.P(*split(x))
        out[p] = {"angles": x.tolist(), "P": P_prev, "exp_cost": sim.energy(*split(x))}
        if objective != "energy":
            out[p]["alpha"] = alpha
        log(f"p={p}: E[cost]={out[p]['exp_cost']:.3f}  P={P_prev:.5f}")
    return out
