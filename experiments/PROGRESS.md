# Teacher–Student Progress Log

How the solver improved round by round. The **student** agent changes the
solver; the **teacher** agent reviews it, explains the ideas
(`LESSONS.md`) and sets the next goal. Detailed per-round notes are in
`LOG.md`; saved angles and metrics in `results/roundN.json`.

All numbers are from local simulation (exact subspace statevector and
`AerSimulator`, seed 7). Nothing was sent to qBraid/SV1. Puzzle: the
four-cube instance from the starter notebook (N = 4).

**Baselines** (same for every round): random legal pick 2/1296 = 0.154%;
random 24-bit string 2/2²⁴ ≈ 1.2 × 10⁻⁷.

## Scoreboard

| Round | Variant | Exact P(solved) | Aer 1000 shots | Qubits | CX | Depth | Transpile |
|---|---|---|---|---|---|---|---|
| 0 | Team notebook (`solution.ipynb`) | 26.35% | 25.5% | 24 | 4610 | 1503 | opt 1 |
| 1 | Student harness reproduces round 0 | 26.35% | 25.5% | 24 | 4610 | 1503 | opt 1 |

## Round 1

**Student did:** rebuilt the notebook's model as `experiments/solver.py`
with a metrics runner and quantum tests. Verified that the fast 1,296-state
subspace simulator matches the real circuit (N = 2, p = 2: max probability
difference 5.6 × 10⁻¹⁶). 35 tests pass (23 classical + 12 quantum).

**Student noticed:**
- Training is fragile: a 2.5 × 10⁻¹⁶ difference in the mixer moved the
  optimum from 26.35% to 26.25%, so gaps of about 0.1 points are noise.
- The notebook minimizes *average cost*, not P(solved); at p = 1 that
  lowers P(solved) from 0.96% to 0.88%.

**Teacher's review:**
- CX breakdown: W states 60 (1.3%), cost layer 3710 (80.5%), XY mixer 840
  (18.2%).
- Most cost-layer gates are wasted. On one-hot states, two choices of one
  cube are never both 1, and each cube's choices sum to 1. Rewriting the
  Hamiltonian with that gives 109 terms instead of 290, exact on all 1,296
  legal picks. Same angles: CX 4610 → 2216, depth 1503 → 792.
- Official CX counts must use the GRADING transpile call; compare variants
  by median over several seeded trainings, not one run.

**Assignment for round 2:** reduced Hamiltonian (required), full vs ring XY
mixer over 5 seeds, then compare training objectives (average cost, CVaR,
Gibbs) if time allows.
