# Experiment log (AI-assisted, Claude Code)

All runs are local (Statevector / AerSimulator, SEED = 7). Nothing was sent to qBraid, SV1 or any QPU.

> Note: this checkout is `main` (83e5f8d). The committed Round 1 entry of this log lives in commit 0e93296 on `luis`. The Round 1 section below is the student's original text. Merge the two when the branches are reconciled.

## Round 1: baseline harness (2026-10-17)

**What changed.** Added `solver.py`, which re-implements the solution notebook's model as importable functions. Also added `run_round.py` (runner) and `tests_quantum.py` (pytest).

**How it was verified.**
- Subspace simulator vs `Statevector(tower_qaoa(...))` at N=2, p=2, 4 angle sets: max |dP| was 5.6e-16 and the mass outside one-hot was 2.2e-16.
- The W state, the mixer and the decoder all pass their tests.
- The cost tensor, Hamiltonian and mixer match the notebook.
- The solved set comes from an independent `solves()`.

**Numbers (N=4, p=7, average-cost COBYLA).** Exact P = 26.35%; Aer 1000 shots = 25.5% (100% valid); 24 qubits; opt 1 gives CX 4610 and depth 1503. Random legal pick: 0.154%. Random bitstring: 1.19e-7.

**Surprises.** A closed-form mixer that differs by 2.5e-16 moved COBYLA to 26.25%, so the default now uses the Operator construction. The average-cost objective can lower P(solved): at p=1 it fell from 0.96% to 0.88%.

## Round 2: smaller cost layer, fair mixer and objective comparison (2026-10-17)

Command: `.venv\Scripts\python.exe experiments/run_round.py 2` (then `run_round.py 2-table` builds the per-variant rows from the saved angles, without retraining). The results are in `results/round2.json` under `variants`. The p=1 start grid is computed once per mixer. Jitter is N(0, 0.05) on the p=1 start angles. Jitter seeds are 0-4 for the mixer comparison and 0-2 for the objectives. COBYLA uses maxiter 80/220/400 and rhobeg 0.35, as in round 1. "CX(G)" and "depth(G)" come from the GRADING call `transpile(qc, basis_gates=["rz","sx","x","cx"])`. "(1)" means opt level 1 with seed 7. Each Aer column is one 1000-shot run (seed 7) of the median-seed angles.

**What changed.**
1. `reduced_hamiltonian(cubes, gauge)` builds the cost Hamiltonian from the cost tensor. It splits the cost into one-cube tables `a_c[k]` and pair tables `B_cd[k,l]`, using reference pick (0,...,0). This removes every intra-cube ZZ term. With `gauge="best"`, each 6x6 pair table is re-referenced to the row and column that leave the fewest non-zeros. Any row-plus-column shift of a pair table only moves weight into single-qubit `rz` terms, because each cube's choices sum to 1. Term counts:
   - full: 290 terms (265 ZZ);
   - reference 0: 109 terms (94 ZZ);
   - best gauge: 97 terms (77 ZZ).
2. The mixer pairs became a parameter (`MIXERS = {"full": 15 pairs, "ring": 6 pairs}`).
3. Training objectives: average cost, CVaR(0.1) and Gibbs (eta = 1). None of them uses the solved set.
4. `train_layerwise` gained `jitter_seed` and `start` options.

**How it was verified (pytest: 59 passed, including tests/test_classical.py).**
- Reduced H energy equals `cost_tensor` on all 1296 legal picks, max error 0, for both gauges. Neither gauge has ZZ terms inside a cube.
- Circuit vs subspace at N=2, p=2: {full, reduced ref 0, reduced best} x {full, ring mixer}, 3 seeds each. In the runner, the max |dP| was at most 5.6e-16 and the mass outside one-hot was at most 2.2e-16.
- Round-1 angles unchanged, full 24-qubit Aer statevector of the transpiled reduced circuits: P(solved) was 0.26346239213612505 (ref 0) and 0.2634623921361232 (best), against 0.26346239213612477 in the subspace. The difference is below 3e-16 and the mass outside one-hot is at most 1.1e-16. With 1000 shots, both gave 255/1000 = 25.5% with 100% valid shots (within ±4.2 points).
- CX at the round-1 angles (ref 0): 2216 at opt 1 (≤ 2250) and 2196 with the GRADING call (≤ 2230). Both have tests.
- Costs are even integers, so gamma has period pi. This has a test.

**Results (N=4, p=7, 24 qubits; random legal pick 0.154%, random bitstring 1.19e-7).**

| variant | seeds | exact P median [min, max] | Aer P (valid) | CX(G) | depth(G) | CX(1) | depth(1) |
|---|---|---|---|---|---|---|---|
| round 1 baseline (full H) | - | 26.35% | 25.5% (100%) | 4590 | 1683 | 4610 | 1503 |
| reduced H ref 0, round-1 angles | - | 26.35% | 25.5% (100%) | 2196 | 972 | 2216 | 792 |
| reduced H best gauge, round-1 angles | - | 26.35% | 25.5% (100%) | 1958 | 908 | 1978 | 733 |
| full mixer, average cost, best H | 0-4 | 26.37% [26.29, 26.48] | 25.5% (100%) | 1958 | 914 | 1978 | 733 |
| ring mixer, average cost, best H | 0-4 | 7.67% [7.65, 7.67] | 7.0% (100%) | 1454 | 760 | 1474 | 741 |
| CVaR(0.1), full mixer, best H | 0-2 | 10.04% [10.03, 10.05] | 10.2% (100%) | 1958 | 908 | 1978 | 733 |
| **Gibbs (eta=1), full mixer, best H** | 0-2 | **35.12% [35.11, 35.12]** | **34.3% (100%)** | **1958** | **920** | **1978** | **733** |

For comparison, the average-cost runs on seeds 0-2 give a median of 26.31% [26.29, 26.48].

**Decisions.**
- **Ring mixer: rejected.** Its median is 18.7 points below the full mixer's, far outside the 1-point rule. It saves 504 CX but loses most of the success probability.
- **Objective: Gibbs (eta = 1).** Its worst run (35.11%) beats average cost's best run (26.48%) by 8.6 points, which is about 45 times the average-cost spread (0.19 points). CVaR(0.1) is clearly worse (10.0%). It lowers the cost of the best 10% of the mass but leaves the mean high (<C> = 5.7).
- **Recommended variant: Gibbs objective + full XY mixer + best-gauge reduced Hamiltonian, p=7.**

**Change vs round 1 (recommended variant vs round 1 baseline).**
- Exact P(solved): 26.35% to 35.12%, which is +8.77 points (+33.3% relative). Aer: 25.5% to 34.3%, which is +8.8 points (+34.5%).
- CX, GRADING call: 4590 to 1958, which is -2632 (-57.3%). CX at opt 1: 4610 to 1978, which is -2632 (-57.1%).
- Depth, GRADING call: 1683 to 920, which is -763 (-45.3%). Depth at opt 1: 1503 to 733, which is -770 (-51.2%).

**Regressions and caveats (honest list).**
- The GRADING (default-level) call gives *deeper* circuits than opt 1 for every variant (for example 920 vs 733). Opt 1 also has 20 more CX.
- Ring mixer: -18.7 points vs the full mixer. CVaR(0.1): -16.3 points vs average cost.
- The seed spreads are tiny (≤ 0.2 points). N(0, 0.05) jitter around the same grid start lands in the same basin, so the spread measures sensitivity to the start point, not how good the optimizer is in general. A wider jitter or a different grid could find other optima.
- The p=1 start grid still uses average cost for every objective. Only 3 seeds were run per objective, and eta was not tuned.
- Brute force solves N=4 in about 0.2 s. No speedup is claimed.

**Run times.**
- Round-1 retraining: 22 s.
- Full-mixer trainings: 20-26 s each. Ring trainings: about 10 s each.
- Trainings for CVaR: about 5 s each; Gibbs: about 22 s each.
- Each Aer run (statevector or 1000 shots): about 35 s.
