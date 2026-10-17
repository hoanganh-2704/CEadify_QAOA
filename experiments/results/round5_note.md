# Round 5 note: the accepted recipe on the 5-cube bonus puzzle

1. Nothing in the recipe changed: I only swapped the puzzle for the challenge's `make_puzzle(5, 16)`, loaded straight from `starter_notebook.ipynb` together with its `count_answers`, and ran the same per-pair reduced Hamiltonian, full XY mixer, Gibbs objective with eta = 1, p = 7, and layer-by-layer COBYLA from the p=1 grid point plus N(0, 0.05) jitter, with seeds 0, 1 and 2.
2. These checks are right because a bigger puzzle is exactly where a model bug would hide. So the test confirms that the cost-0 picks are the same picks an independent `solves()` brute force finds, and that their count equals `count_answers`. It also checks that the Hamiltonian gives the right cost on all 7,776 legal picks, and it recomputes every P(solved) from the saved angles, so the reported numbers cannot drift from the circuit that produced them.
3. I wrote `experiments/tests_round5.py` first and ran `.venv\Scripts\python.exe -m pytest experiments/tests_round5.py -q -p no:cacheprovider` (red), then `.venv\Scripts\python.exe experiments/run_round.py 5`, then the round-5 tests and the full suite (green).
4. At N = 5 the exact subspace P(solved) was 9.332%, 9.333% and 9.333% for seeds 0, 1 and 2 (median 9.333%, min 9.332%, max 9.333%), against a random legal pick of 0.0257%. The circuit has 30 qubits, 161 ZZ terms, and 3354 CX and depth 1147 from `transpile(qc, basis_gates=["rz","sx","x","cx"])`. Each seed took about 25 s to train, while the starter's brute force over all 7,962,624 orientations took 7.4 s and `count_answers` over the 7,776 cases took 0.01 s.

All P(solved) values here are exact numbers from the 6^5 legal-subspace simulator. No Aer run was made at 30 qubits (a full statevector would need about 16 GB), so there are no shot rates. No speedup is claimed: brute force is faster than training even one seed.

Red pytest line (before implementing, tests_round5.py only):
`1 failed, 4 errors in 3.76s`

Green pytest lines (after implementing):
- `experiments/tests_round5.py`: `5 passed in 2.73s`
- Full suite (`experiments/tests_quantum.py experiments/tests_round2_review.py experiments/tests_round3_review.py experiments/tests_round4.py experiments/tests_round5.py tests`): `95 passed in 42.35s`

## N = 4 vs N = 5 (same recipe)

| | N = 4 (accepted round 4) | N = 5 (this round) |
|---|---|---|
| puzzle | `CUBES` | `make_puzzle(5, 16)` |
| qubits | 24 | 30 |
| legal picks / solved picks | 1,296 / 2 | 7,776 / 2 |
| ZZ terms (per-pair reduced H) | 77 | 161 |
| CX (GRADING call) | 1958 | 3354 |
| depth (GRADING call) | 907 | 1147 |
| exact P(solved), median [min, max] | 35.12% [35.11, 35.12] (seeds 0–4) | 9.33% [9.33, 9.33] (seeds 0–2) |
| random legal pick | 0.154% | 0.0257% |
| random bitstring | 1.19e-7 | 1.86e-9 |
| training time per seed | 20–22 s | 24–26 s |
| brute force (24^N orientations) | not re-measured this round | 7.4 s |
| `count_answers` (6^N cases) | not re-measured this round | 0.01 s |

The N = 4 training times are from `results/round4.json`, and every other N = 4 entry comes from the accepted round-4 and round-2 results. From N = 4 to N = 5, P(solved) falls from 35.12% to 9.33% while CX grows 1.7x. The ratio to a random legal pick goes from about 228x to about 363x.
