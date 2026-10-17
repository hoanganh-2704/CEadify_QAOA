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
| 1 | Same circuit, GRADING transpile call | 26.35% | 25.5% | 24 | 4590 | 1683 | GRADING |
| 2 | Reduced Hamiltonian (best gauge), round-1 angles | 26.35% | 25.5% | 24 | 1958 | 908 | GRADING |
| 2 | Ring mixer (6 pairs), avg cost, 5 seeds | 7.67% median | 7.0% | 24 | 1454 | 760 | GRADING — rejected |
| 2 | CVaR(0.1) objective, 3 seeds | 10.04% median | 10.2% | 24 | 1958 | 908 | GRADING — rejected |
| **2** | **Gibbs objective (η=1) + full mixer + reduced H, 3 seeds** | **35.12% median** | **34.3%** | **24** | **1958** | **920** | **GRADING** |

From round 2 on, the official CX/depth use the GRADING call
`transpile(qc, basis_gates=["rz","sx","x","cx"])` so every team counts the
same way.

**Best so far vs the team notebook:** exact P(solved) 26.35% → 35.12%
(+8.77 points, +33%), CX 4590 → 1958 (−57%), depth 1683 → 920 (−45%).

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

## Round 2

> **Status: provisional.** This round bundled three changes (Hamiltonian
> reduction, mixer study, objective study) in one run and retrained the
> angles it called "round-1 angles." Under the protocol in `PROTOCOL.md`
> (adopted after this round) it is being redone one change at a time,
> starting with the reduced Hamiltonian only. Treat the numbers below as
> leads, not accepted results, until each change passes its own review.

**Student did:**
1. **Reduced Hamiltonian.** Rebuilt H from the cost tensor using the one-hot
   identities, then picked the reference choice ("gauge") per cube that
   gives the fewest ZZ terms (94 → 77). Exact on all 1,296 legal picks
   (error 0). The full 24-qubit Aer statevector with round-1 angles matches
   26.35% to under 3 × 10⁻¹⁶. CX 4590 → 1958 with the same success rate.
2. **Mixer comparison (5 seeds each).** Ring mixer: 7.67% median vs full
   mixer 26.37%, 18.7 points worse. Rejected, even though it saves about
   500 CX.
3. **Objective comparison (3 seeds each).** Average cost 26.37%,
   CVaR(0.1) 10.04%, **Gibbs (η=1) 35.12%**. Gibbs's worst run beats
   average cost's best run by 8.6 points, about 45× the seed spread.

**Change vs round 1:** exact P +8.77 points (+33%); CX −2632 (−57%);
depth −763 (−45%). 59 tests pass.

**Caveats the student reported:** the seed spread is small because start
angles were only jittered slightly, so other optima weren't explored; η
was not tuned; the GRADING call gives deeper circuits than opt 1 (920 vs
733).

**Teacher's review under the new protocol** (`results/round2_review.md`):
**not yet.**
- Passed: the reduced Hamiltonian (both gauges) matches `cost_tensor` on
  all 1,296 legal picks, and at the saved round-1 angles its legal-subspace
  state matches round 1 to 1e-9 (N = 4; the N = 2 Qiskit circuits match
  too).
- Failed: `round2.json` used retrained angles, which differ from
  `round1.json` by up to 1.96 × 10⁻³, instead of loading them. The
  student's four-sentence note is missing.
- Red tests (`experiments/tests_round2_review.py`):
  `test_round2_results_used_the_saved_round1_angles`,
  `test_round2_note_explains_the_round`. Teacher's run: 2 failed, 64 passed.
- The teacher also removed the CX-budget and exact-term-count asserts from
  `tests_quantum.py`, because rule 1 makes CX a measurement, not a target.
- The mixer and objective studies were not reviewed and remain leads.

**What we learned (provisional):** the training objective mattered more than the mixer
shape. Fewer two-qubit gates came from removing terms that are constant on
the legal states, not from a sparser mixer.
