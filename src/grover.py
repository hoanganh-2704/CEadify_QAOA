"""Grover search on the compact encoding (3 qubits per cube) with an oracle built only from the puzzle rules.

The oracle flips the phase of a code string when, on the front/back sides and on the left/right sides,
every colour sits on exactly two of the chosen pairs. It never sees an answer. The search runs over the
6^N valid codes (valid_prep), so with M = 2 answers it needs K = 19 iterations at N = 4.

Invariant G1: grover_circuit returns a circuit on exactly the 3N data qubits. runtime.prepare_safe then
composes it onto a wider register whose idle qubit 0 the transpiler uses as a clean ancilla for every
multi-controlled gate; that is what brings K = 19 down to about 4,000 CX. Never build the oracle or the
Grover operator on a circuit that already contains the spare qubit.
"""
import itertools
import math

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import StatePreparation
from qiskit.quantum_info import Statevector

from src.puzzle import CHOICES, letters_of

try:                                                    # Qiskit 2.x: Rust synthesis of a Boolean expression
    from qiskit.circuit.library import PhaseOracleGate
except ImportError:                                     # Qiskit 1.3: no PhaseOracleGate (see ORACLE_BACKEND below)
    PhaseOracleGate = None
try:
    from qiskit.circuit.library import grover_operator  # Qiskit >= 1.3 function
except ImportError:                                     # older: the GroverOperator class
    from qiskit.circuit.library import GroverOperator

    def grover_operator(oracle, state_preparation=None):
        return GroverOperator(oracle, state_preparation=state_preparation).decompose()

# Which oracle construction is in use: "synthesis" (PhaseOracleGate, all reported numbers) or "diagonal" (Qiskit 1.3
# fallback: the same rule evaluated on every code string and applied as a diagonal phase gate; functionally the same
# oracle, but its gate count is not comparable and is not reported).
ORACLE_BACKEND = "synthesis" if PhaseOracleGate is not None else "diagonal"

UNIFORM6 = np.array([1, 1, 1, 1, 1, 1, 0, 0]) / math.sqrt(6)   # equal weight on codes 0..5, none on 6, 7
CX_PER_ITER_N4 = 209    # measured: (CX at K=19 - CX at K=1) / 18 = (3987 - 225) / 18 after prepare_safe
_ORACLES = {}


def _code_literal(c, code):
    """Boolean term that is true when cube c holds the 3-bit code (bit i on variable x{3c+i})."""
    bits = [(code >> i) & 1 for i in range(3)]
    return "(" + " & ".join(f"x{3 * c + i}" if b else f"~x{3 * c + i}" for i, b in enumerate(bits)) + ")"


def _exactly_two(terms):
    """Boolean term that is true when exactly two of the given terms are true."""
    out = []
    for i, j in itertools.combinations(range(len(terms)), 2):
        out.append("(" + " & ".join(t if m in (i, j) else f"~{t}" for m, t in enumerate(terms)) + ")")
    return "(" + " | ".join(out) + ")"


def _codes_term(c, codes):
    """Boolean term: cube c holds one of the given codes (false constant when the list is empty)."""
    return "(" + " | ".join(_code_literal(c, k) for k in codes) + ")" if codes else "(x0 & ~x0)"


def oracle_expression(cubes):
    """The rules as one Boolean formula: for each side pair and colour, the colour appears exactly twice.

    A cube whose chosen pair shows the colour once contributes one term; a same-colour pair such as "BB" shows it
    twice (weighted degree, as in count_answers), so such a cube gets a second term that is true exactly for those
    codes. Cubes without a same-colour pair get no extra term, so instances like CUBES keep the original formula.
    """
    n = len(cubes)
    clauses = []
    for side in (0, 1):                         # 0: front/back pair, 1: left/right pair
        for colour in letters_of(cubes):
            terms = []
            for c in range(n):
                once = [k for k, pick in enumerate(CHOICES) if colour in cubes[c][pick[side]]]
                twice = [k for k, pick in enumerate(CHOICES) if cubes[c][pick[side]] == colour + colour]
                terms.append(_codes_term(c, once))
                if twice:
                    terms.append(_codes_term(c, twice))
            clauses.append(_exactly_two(terms))
    return " & ".join(clauses)


def rule_holds(cubes, codes):
    """The same rule evaluated classically on one code per cube (weighted degree exactly two per side and colour)."""
    letters = letters_of(cubes)
    for side in (0, 1):
        for colour in letters:
            if sum(cubes[c][CHOICES[k][side]].count(colour) for c, k in enumerate(codes)) != 2:
                return False
    return True


def _diagonal_oracle(cubes):
    """Qiskit 1.3 fallback: a diagonal gate with phase -1 on every code string where rule_holds (illegal codes 6, 7
    are never marked). It evaluates the rules on all 2^(3N) strings, so it is a truth-table oracle: correct, but
    its synthesised gate count means nothing and is not reported."""
    n = len(cubes)
    diag = np.ones(2 ** (3 * n))
    for codes in itertools.product(range(6), repeat=n):
        if rule_holds(cubes, codes):
            diag[sum(k << (3 * c) for c, k in enumerate(codes))] = -1
    from qiskit.circuit.library import DiagonalGate
    qc = QuantumCircuit(3 * n, name="oracle")
    qc.append(DiagonalGate(list(diag)), range(3 * n))
    return qc


def build_oracle(cubes):
    """3N-qubit phase oracle from oracle_expression (synthesis takes about 5 s at N = 4 and 2 min at N = 5)."""
    key = tuple(tuple(c) for c in cubes)
    if key not in _ORACLES:
        nq = 3 * len(cubes)
        if ORACLE_BACKEND == "synthesis":
            gate = PhaseOracleGate(oracle_expression(cubes), var_order=[f"x{i}" for i in range(nq)])
            qc = QuantumCircuit(nq, name="oracle")
            qc.append(gate, range(nq))
        else:
            qc = _diagonal_oracle(cubes)
        _ORACLES[key] = qc
    return _ORACLES[key]


def valid_prep(n):
    """3N-qubit state preparation: each cube in an equal mix of its 6 valid codes (same state as compact.uniform6)."""
    qc = QuantumCircuit(3 * n, name="valid6")
    for c in range(n):
        qc.append(StatePreparation(UNIFORM6), [3 * c, 3 * c + 1, 3 * c + 2])
    return qc


def grover_iterations(n, m=2):
    """Best number of Grover iterations for m answers among 6^n valid codes: the better of the two integers
    around pi / (4 theta) - 1/2 (flooring alone is not always optimal, e.g. N = 3, M = 2 wants 8, not 7)."""
    if not 1 <= m <= 6 ** n:
        raise ValueError(f"m must be between 1 and 6^{n}")
    theta = math.asin(math.sqrt(m / 6 ** n))
    k0 = max(0, math.floor(math.pi / (4 * theta) - 0.5))
    return max((k0, k0 + 1), key=lambda k: grover_success(n, k, m))


def grover_success(n, k, m=2):
    """Textbook success probability sin^2((2k+1) theta) after k iterations."""
    theta = math.asin(math.sqrt(m / 6 ** n))
    return math.sin((2 * k + 1) * theta) ** 2


def grover_circuit(cubes, k):
    """Measurement-free 3N-qubit Grover circuit: valid_prep, then k Grover iterations (no spare qubit, G1)."""
    n = len(cubes)
    prep = valid_prep(n)
    step = grover_operator(build_oracle(cubes), state_preparation=prep)
    qc = QuantumCircuit(3 * n, name=f"grover_K{k}")
    qc.compose(prep, inplace=True)
    for _ in range(k):
        qc.compose(step, inplace=True)
    return qc


def marked_states(cubes):
    """Basis indices whose sign the oracle flips, found by running it on the uniform superposition (N <= 5)."""
    nq = 3 * len(cubes)
    if nq > 15:
        raise ValueError("marked_states simulates 2^(3N) amplitudes; use N <= 5")
    qc = QuantumCircuit(nq)
    qc.h(range(nq))
    qc.compose(build_oracle(cubes), inplace=True)
    amps = Statevector(qc).data
    return [int(i) for i in np.flatnonzero(amps.real < 0)]


def resource_estimate(ns=(5, 6, 7, 8), cx_per_iter=None):
    """Iterations K and an estimated CX count for larger N (not run): K x CX per iteration, scaled linearly in N."""
    out = []
    for n in ns:
        k = grover_iterations(n)
        per = cx_per_iter if cx_per_iter is not None else CX_PER_ITER_N4 * n / 4
        out.append({"N": n, "K": k, "P_theory": grover_success(n, k), "qubits": 3 * n + 2,
                    "cx_per_iter": round(per), "cx_estimate": round(k * per), "label": "estimate, not run"})
    return out
