# Round 7 note: local noise simulation (N = 3)

1. The only change is that I ran the accepted recipe's transpiled circuit through an Aer noise model. The recipe is the per-pair reduced Hamiltonian, full XY mixer, Gibbs eta = 1, layer-by-layer COBYLA from the p=1 grid point with N(0, 0.05) jitter seed 0, trained once and kept at every p. The puzzle is the 3-cube `make_puzzle(3, 0)` (18 qubits): seed 0 is already the smallest seed with an answer, and `count_answers` gives 16 of 216 cases. I ran p = 1, 2, 3 and 4 with 2000 shots and simulator seed 7. **I dropped p = 6**, because a timing run of one noisy 2000-shot simulation at p = 6 took 355 s, which would have pushed the round past the time budget.
2. The checks are right because they test the counting before the noise: with the noise model off, the same transpile-and-sample pipeline must land within 3 binomial standard errors of the exact P(solved) with every shot one-hot. With noise on, the post-selected count must equal the number of shots that decode as one-hot. Every rate in the table is recomputed from the counts saved in round7.json, and every solved shot passes `solves()`.
3. I wrote `experiments/tests_round7.py` first and ran `.venv\Scripts\python.exe -m pytest experiments/tests_round7.py -q -p no:cacheprovider` (red), then `.venv\Scripts\python.exe experiments/run_round.py 7`, then the round-7 tests and the full suite (green). After the red run, I changed two things in my own test. I removed a leftover no-op line. I also let it accept the p list with the dropped p recorded in `dropped_p`.
4. Results:
   - Noiseless Aer matched the exact P(solved) at every p, with 100% one-hot shots.
   - With noise, P(solved) over all shots fell from 4.75% at p = 1 to 0.30% at p = 4. That is already below the 7.4% random legal pick at p = 1.
   - The one-hot fraction collapsed from 17.4% to 1.6%.
   - Post-selecting the one-hot shots brought P(solved) back to 27.2%, 32.8%, 22.8% and 18.8%. All of these are above the 7.4% random baseline that applies after post-selection. But they rest on only 349, 131, 57 and 32 kept shots, so their standard errors grow from about 2 to about 7 points.

**Stated noise assumptions (not any specific device):**
- Depolarizing error with parameter 1e-2 on every `cx`.
- 5e-4 on `sx` and `x`.
- None on `rz`, which is a virtual frame change.
- Symmetric 2% readout flip on every qubit.

The circuit is the GRADING-call circuit `transpile(qc, basis_gates=["rz","sx","x","cx"])` with no coupling map. So there are no routing SWAPs, which makes this an optimistic setting. This is a local simulation only, and I make no hardware claim. I am not picking a p.

Red pytest line (before implementing, tests_round7.py only):
`2 failed, 5 errors in 21.74s`

Green pytest lines (after implementing):
- `experiments/tests_round7.py`: `7 passed in 3.81s`
- Full suite (`experiments/tests_quantum.py experiments/tests_round2_review.py ... experiments/tests_round7.py tests`): `106 passed in 51.50s`

## Per-p table (N = 3, `make_puzzle(3, 0)`, 18 qubits, 16 answers of 216 legal picks)

Baselines: random legal pick 7.41%; random 18-bit string 6.10e-5; random string after one-hot post-selection 7.41% (a uniform string that happens to be one-hot is a uniform legal pick).

| p | exact P | noiseless Aer P | noisy P (all shots) | one-hot fraction | post-selected P (kept shots) | P × 0.99^CX | CX | depth | noisy run time |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 36.38% | 36.95% | 4.75% | 17.4% | 27.22% (95/349) | 4.87% | 200 | 161 | 95 s |
| 2 | 61.58% | 63.05% | 2.15% | 6.6% | 32.82% (43/131) | 1.49% | 370 | 282 | 131 s |
| 3 | 74.83% | 74.50% | 0.65% | 2.9% | 22.81% (13/57) | 0.33% | 540 | 397 | 186 s |
| 4 | 82.53% | 82.15% | 0.30% | 1.6% | 18.75% (6/32) | 0.07% | 710 | 519 | 240 s |
| 6 | dropped (one noisy run took 355 s) | | | | | | | | |

Noiseless Aer runs took 0.1–0.2 s each. The training to p = 4 is not separately timed. CX and depth come from the GRADING call.

The simple estimate P × 0.99^CX tracks the noisy all-shot rate at p = 1 (4.87% vs 4.75%). At higher p it predicts less than was measured, partly because noise can turn a wrong shot into a solved one. With 16 of 216 picks solved, a noise-scrambled shot can still decode to a solved tower by chance.
