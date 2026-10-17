# Teacher lessons (AI-assisted review, Claude Code)

Each round, the teacher reviews the student's code and numbers, re-checks at least one claim, explains the ideas behind the next steps, and sets the next assignment. All runs are local simulation only.

## Round 1

### What I checked myself

- I read `solver.py`, `run_round.py`, `tests_quantum.py`, `LOG.md` and `results/round1.json`.
- I rebuilt the CX count piece by piece with the same transpile call (`basis_gates=["rz","sx","x","cx"]`, opt level 1, seed 7). The pieces add up exactly to the student's 4610:

| part of the circuit | CX per copy | copies | CX total | share |
|---|---|---|---|---|
| W states (4 cubes) | 60 | 1 | 60 | 1.3% |
| cost layer (24 Z + 265 ZZ terms, 2 CX per ZZ) | 530 | 7 | 3710 | 80.5% |
| XY mixer (4 cubes x 15 pairs, 2 CX per `XXPlusYYGate`) | 120 | 7 | 840 | 18.2% |
| **total** | | | **4610** | |

- Of the 265 ZZ terms, 57 act inside one cube and 208 act between two cubes.
- Every legal cost is an even integer (0, 2, ..., 20).
- I built a smaller Hamiltonian that only keeps what matters on the one-hot states (see Lesson 1). It equals `cost_tensor` on all 1296 legal picks with max error 0. It has 109 terms (94 ZZ) instead of 290 (265 ZZ). With the round-1 angles unchanged, the circuit drops from **4610 to 2216 CX** and from **depth 1503 to 792** (opt level 1). With the GRADING call (default opt level, Qiskit 2.6) it is 4590 to 2196 CX. P(solved) does not change, because the state on the legal subspace is the same (Lesson 1).

### What was good

- A single importable harness, with a fast 6^N simulator checked against the real circuit's statevector (max |dP| about 5.6e-16, no mass outside one-hot). This check makes every later number trustworthy.
- The solved set comes from an independent `solves()` and is checked against cost == 0, not assumed.
- Honest baselines (random legal pick 0.154%, random bitstring 1.19e-7), Aer cross-check, and no speedup claim.
- Both surprises are real findings: training is sensitive to tiny changes, and the average-cost objective is not the same as P(solved).

### What was weak

1. **80% of the two-qubit gates are spent on the cost layer, and over half of those do nothing useful.** The Hamiltonian was written for all 2^24 bitstrings, but the state only ever lives on the 1296 one-hot ones.
2. **CX counts used opt level 1, but GRADING says to count with `transpile(qc, basis_gates=[...])`, which is the default level.** Report the GRADING call as the official number. Level 1 can stay as an extra column.
3. **One training run per variant is not enough to compare variants.** The "0.1 point noise floor" is one sample. COBYLA from a slightly different start can land in a different local optimum. Treat training as a random process and report a spread.
4. **The trained gammas sit near 3.0 rad. Nobody asked why.** See Lesson 3. Judges like an explanation of the angles you report.

### Lesson 1: Only the legal subspace matters, so drop terms that are constant there

The XY mixer and the W state never leave the one-hot subspace (exactly one qubit set per cube). On that subspace, two facts hold for every cube c:

- x_{c,i} x_{c,j} = 0 when i != j, because two choices of the same cube are never both 1. So every ZZ term **inside** a cube is a combination of single Z terms and a constant there. It costs 2 CX and does nothing that an `rz` cannot do.
- x_{c,0} + ... + x_{c,5} = 1. So for two cubes c and d, adding u(k) + v(l) to the pair table B_cd[k, l] does not change the cost of any legal tower. It only moves weight into one-body (Z) terms. You can use this freedom (a "gauge" choice) to make a full row and column of each 6x6 pair table zero. For example, measure everything relative to choice 0:

  B'[k, l] = B[k, l] - B[k, 0] - B[0, l] + B[0, 0]

A clean way to build the smaller Hamiltonian straight from the cost tensor (with r = the all-zeros pick):

- a_c[k] = cost(cube c = k, others = 0) - cost(r)
- B_cd[k, l] = cost(c = k, d = l, others 0) - cost(c = k) - cost(d = l) + cost(r)

Then cost = cost(r) + sum a_c[k_c] + sum B_cd[k_c, k_d] exactly. This works because the degree cost is a sum of squares of linear terms, so it has no 3-cube terms. Check this by brute force over all 1296 picks; it should be exact. Then write each x as (1 - Z)/2 to get Paulis.

Why the answer does not change: the cost layer is diagonal. On every legal bitstring the new Hamiltonian gives the same energy, up to a constant, which is a global phase. So exp(-i gamma H) acts the same on the legal subspace. The angles you already trained are still optimal. **A circuit-equivalent rewrite needs no retraining, and its proof is an exact equality, not a statistical one.**

What to say to judges: "Our Hamiltonian only needs to be right on the states the mixer can reach. Using the one-hot rule, we removed terms that are constant there. That cut the two-qubit gates in half with exactly the same output distribution."

### Lesson 2: Changes that keep the circuit's output vs. changes to the model

There are two kinds of variants, and they need different evidence:

- **Equivalent rewrites** (Lesson 1, better transpiling, gate reordering that commutes). Proof: same angles, same subspace state to about 1e-12, same P(solved). No training noise is involved.
- **Model changes** (a different mixer, a different objective, a different p). These change the landscape, so you must retrain. A single COBYLA run is one draw from a noisy process. Compare **distributions**: run K trainings with different (seeded) jitters of the starting angles, and report the median and min/max of P(solved) for each variant. Only call variant A better than B when A's median beats B's max, or at least when the gap is well beyond the spread. Use the same seeds, maxiter and p for both.

A ring XY mixer is a good example of a model change. Using pairs (0,1),(1,2),...,(5,0) per cube instead of all 15 pairs still keeps the one-hot subspace and still connects every choice to every other choice over several layers. It costs 6 instead of 15 `XXPlusYYGate`s per cube per layer (336 instead of 840 CX at p=7). Whether it reaches the same P(solved) is an empirical question, which is exactly what the K-run comparison is for.

### Lesson 3: Integer costs make gamma periodic

All legal costs here are even integers. That is no accident: on each axis the colour degrees add up to 2N = 8, and (d - 2)^2 has the same parity as d. So exp(-i gamma C) is the same for gamma and gamma + pi. The p=1 grid over [0, pi] covers exactly one period, and a trained gamma of about 3.0 is the same as about -0.14. "Small negative gamma with small positive beta" is the usual QAOA picture, just with a sign convention. Knowing the period also tells you where to start a grid, and why two very different-looking angle sets can give the same state.

### Lesson 4: What to train on

The notebook minimizes the average cost <C>. This is smooth and easy to estimate from shots. But it rewards moving weight from cost 10 to cost 4 as much as from cost 2 to cost 0, while we only score cost 0. Two standard objectives focus on the low end and do **not** require knowing the solution in advance (they only use the cost function):

- **CVaR_alpha:** the mean cost of the best alpha fraction of the distribution (for example alpha = 0.1). On the exact distribution, sort the costs and average the lowest alpha of the probability mass.
- **Gibbs objective:** -log( sum_x p(x) exp(-eta C(x)) ) with eta around 1 to 2. Small eta behaves like <C>, large eta behaves like -log P(C = 0).

Optimizing P(C = 0) directly is also allowed here, because cost 0 means "solved" by construction. But at small p this landscape is almost flat (around 0.15% everywhere), so COBYLA has little to follow. That fits the student's p=1 finding. Whatever you choose, report P(solved) as the score, and report the objective only as the training tool.

### Round 2 assignment (about 10 minutes of compute)

**Priority 1: Exact one-hot Hamiltonian reduction (required).**
- Add `reduced_hamiltonian(cubes)` to `solver.py` (build it from the cost tensor as in Lesson 1, with reference choice 0). Keep the old one for comparison.
- Success: (a) energy equals `cost_tensor` on all 1296 legal picks with max error < 1e-9 (pytest); (b) subspace-vs-statevector test passes for the reduced circuit at N=2, p=2 (max |dP| < 1e-9, mass outside < 1e-9); (c) with the **round-1 angles unchanged**, N=4: exact P(solved) = 26.35% (to 1e-9 of the round-1 value), CX <= 2250 at opt level 1 and <= 2230 with the GRADING default call; (d) Aer 1000 shots within +/-4.2 points (3 sigma) of 26.35%, and 100% valid.
- Optional: the best reference choice per cube pair gives 77 instead of 94 ZZ terms. Do this only if you can explain it in one sentence.

**Priority 2: A fair mixer comparison, full 15-pair vs ring 6-pair (both on the reduced Hamiltonian).**
- Add a seeded jitter option to `train_layerwise` (for example, add N(0, 0.05) to the p=1 grid angles, seeds 0-4). Run K = 5 trainings per mixer at p=7 with the same settings.
- Report median/min/max P(solved), CX and depth for each (GRADING call). Also report the K = 5 spread of the full mixer by itself, which replaces the "0.1 point" noise guess.
- Success: the table exists. The ring mixer is adopted only if its median P(solved) is within 1 point of the full mixer's median (or better). It should reach about 1.7k CX or less. Add a test that the ring mixer's subspace simulator matches the circuit at N=2 (< 1e-9).

**Priority 3 (only if time remains): Objective comparison.** On the winning mixer, K = 3 seeds each: <C> (current) vs CVaR_0.1 vs Gibbs (eta = 1). Report median P(solved). Do not pick a winner on a gap smaller than the measured spread.

Reporting: append a "Round 2" section to `LOG.md` with the table (GRADING-call CX as the main number), the seeds, and run times. Keep every claim tied to a test or a printed number.
