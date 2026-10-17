# Round 7 assignment (one change: add a stated noise model)

**Question:** under a stated, typical gate-and-readout noise model, at which depth p does the accepted recipe stop beating the random baseline? Does throwing away shots that are not one-hot recover enough to matter? Measure this locally on a puzzle small enough to simulate with noise. It replaces the 0.995^CX estimate from round 6.

**Setup (stated assumptions, not a model of any specific device):**
- **Puzzle:** `make_puzzle(3, s)` (18 qubits), where s is the smallest seed ≥ 0 that `count_answers` says has at least one answer. Record s and the answer count.
- **Angles:** the accepted recipe (reduced H, full XY mixer, Gibbs eta = 1, layer-by-layer COBYLA, N(0, 0.05) jitter), jitter seed 0 only, trained once to p = 6, keeping the angles at every p (as in round 6).
- **Depths:** p = 1, 2, 3, 4, 6.
- **Circuit:** the transpiled GRADING circuit `transpile(qc, basis_gates=["rz","sx","x","cx"])`, the same object for every simulation. There is no coupling map, so routing SWAPs are not included, and this is an optimistic setting. Say so in the note.
- **Noise (Aer `NoiseModel`):** depolarizing error 1e-2 on every `cx`, 5e-4 on `sx` and `x`, none on `rz` (virtual), and a symmetric readout error of 2% per qubit.
- **Runs:** AerSimulator, 2000 shots, `seed_simulator = 7`.

**Report (`results/round7.json` and the four-sentence `round7_note.md`), one row per p:**
- exact P(solved);
- noiseless-Aer P(solved);
- noisy P(solved) over all shots;
- the one-hot fraction of shots;
- noisy P(solved) post-selected on one-hot shots;
- P(solved) × (1 − 1e-2)^CX for comparison;
- CX/depth;
- run time.

Also report the random-legal and random-bitstring baselines. Every shot that counts as solved must pass `solves()`. Do not pick a p, and make no hardware claim.

**Invariant the test checks first:**
1. With the noise model off, the same pipeline's P(solved) agrees with the exact subspace P(solved) at every p within 3 binomial standard errors, and 100% of shots are one-hot.
2. With noise on, the post-selected count equals the number of shots that decode as one-hot.
3. Every reported rate recomputes from the saved counts.
