# Round 10 note: Grover amplitude amplification vs QAOA on the legal picks

## Scope (written before the test was touched)

I am doing only part (a), the ideal-oracle analysis on the exact subspace simulator for N = 3 (`make_puzzle(3, 0)`) and N = 4 (`CUBES`). I am skipping optional part (b), the gate-level colour-degree check, because the round has a hard stop at about 14:20–14:25. I give no oracle CX number, measured or bounded, and I do not guess one. Shot counts do not apply: everything here is exact subspace simulation.

## The round

1. The only change is a Grover search over the same legal picks, simulated on the exact subspace: start in the W-product state (uniform over the 6^N legal picks), flip the sign of exactly the cost-0 picks (the ideal oracle), then reflect about the start state, and repeat k times. I ran it for N = 3 (`make_puzzle(3, 0)`, 16 answers in 216) and N = 4 (`CUBES`, 2 answers in 1,296), and put it next to QAOA's P(solved) read from round7.json (N = 3) and round6.json (N = 4).
2. The checks are right because Grover's behaviour is known exactly, so the simulation can be held to the formula. The test requires that the oracle marks exactly the picks the starter's `solves()` brute force finds, with `count_answers` agreeing. It requires that every reported P(solved) after k iterations equals sin²((2k+1)θ) with sin²θ = M/6^N to 1e-9 and also recomputes from my simulator. And the QAOA numbers must equal the saved round-6/7 fields rather than being typed in.
3. I wrote the scope above and `experiments/tests_round10.py` first and ran `.venv\Scripts\python.exe -m pytest experiments/tests_round10.py -q -p no:cacheprovider` (red), then `.venv\Scripts\python.exe experiments/run_round.py 10`, then the round-10 tests and the full suite (green).
4. The results:
   - **N = 3:** ideal Grover peaks at k = 2 oracle calls with P(solved) = 96.34%. QAOA reaches 36.38%, 61.58%, 74.83% and 82.53% at p = 1 to 4.
   - **N = 4:** Grover peaks at k = 19 oracle calls with 99.85%. QAOA reaches 55.19% at p = 10. Round for round, Grover is slightly ahead at 1–3, the two tie at 4 (11.99% vs 12.00%), and QAOA is ahead from 5 to 10 (for example 35.12% vs 30.90% at 7). But Grover keeps climbing to its peak while QAOA was only run to 10.

**Caveats:**
- Picking the best k (2 and 19) uses the answer count M, which QAOA never needs. Without M, the standard remedy is an exponential-search schedule that tries random k from a growing range (or quantum counting to estimate M first), at a constant-factor cost in oracle calls.
- A Grover "call" and a QAOA layer are not the same price. I skipped part (b), so I have no gate count for the oracle, and this table compares rounds, not two-qubit gates.
- No speedup is claimed: brute force solves both puzzles in well under a second.

Red pytest line (before implementing, tests_round10.py only):
`2 failed, 4 errors in 4.09s`

Green pytest lines (after implementing):
- `experiments/tests_round10.py`: `6 passed in 2.67s`
- Full suite (`experiments/tests_quantum.py ... experiments/tests_round10.py tests`): `127 passed in 64.96s`

## Comparison table (exact P(solved); Grover = ideal oracle, so no oracle CX is known)

**N = 3, `make_puzzle(3, 0)`: M = 16 of 216, random legal 7.41% (QAOA from round 7)**

| k or p | Grover P after k oracle calls | QAOA P at depth p | QAOA CX (GRADING) |
|---|---|---|---|
| 0 | 7.41% | – | – |
| 1 | 54.15% | 36.38% | 200 |
| 2 | 96.34% **(best k)** | 61.58% | 370 |
| 3 | 87.68% | 74.83% | 540 |
| 4 | 37.67% | 82.53% | 710 |
| 5 | 1.19% | – | – |

**N = 4, `CUBES`: M = 2 of 1,296, random legal 0.154% (QAOA = round 6 median of seeds 0–2)**

| k or p | Grover P after k oracle calls | QAOA P at depth p | QAOA CX (GRADING) |
|---|---|---|---|
| 0 | 0.15% | – | – |
| 1 | 1.38% | 1.14% | 314 |
| 2 | 3.81% | 2.85% | 588 |
| 3 | 7.38% | 6.34% | 862 |
| 4 | 11.99% | 12.00% | 1136 |
| 5 | 17.55% | 20.29% | 1410 |
| 6 | 23.90% | 27.39% | 1684 |
| 7 | 30.90% | 35.12% | 1958 |
| 8 | 38.37% | 41.83% | 2232 |
| 9 | 46.12% | 48.52% | 2506 |
| 10 | 53.97% | 55.19% | 2780 |
| 19 | 99.85% **(best k)** | – | – |
| 22 | 96.15% | – | – |

Both tables were generated directly from `results/round10.json`, not typed. The full Grover curves run from k = 0 to 5 for N = 3 and k = 0 to 22 for N = 4.
