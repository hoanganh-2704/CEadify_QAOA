# Round 10 assignment (one change: Grover amplitude amplification on the legal subspace, compared with QAOA)

This round is requested by the user. It runs after the round-9 review.

**Question:** if you replace QAOA's cost-and-mixer layers with Grover amplitude amplification over the same legal picks, how do P(solved), the number of oracle calls, and the circuit cost compare with QAOA at the same puzzle sizes? Grover's advantage is provable and quadratic, but it is counted in oracle queries. Whether it also wins in two-qubit gates is something you measure here, not something you claim.

**Setup:**
- **State preparation A:** the product of W states, so the search runs over the 6^N legal picks, not over 2^(6N) bitstrings.
- **Oracle:** a phase flip (−1) on exactly the cost-0 picks.
- **Diffusion:** 2|A⟩⟨A| − I, a reflection about the W-product state. One Grover iteration is the oracle followed by the diffusion.
- **Puzzles:**
  - N = 3: `make_puzzle(3, 0)`, the round-7/8 puzzle;
  - N = 4: the starter `CUBES`.

**(a) Required: ideal-oracle analysis on the exact subspace simulator.**
- For each N, report P(solved) for k = 0 up to a little past the first peak.
- Report the k that maximizes P(solved) and the oracle calls at that k.
- Put these next to QAOA's exact P(solved) against p, from round 7 (N = 3) and round 6 (N = 4).
- State plainly that choosing the best k uses the number of answers M, which the solver normally does not know. Name the standard remedy (an unknown-M or adaptive schedule) in one sentence; you do not need to run it.

**(b) Optional: only if (a) is green with time to spare, and N = 3 only.**
- Build one gate-level piece of a real oracle: one colour's degree check on one axis, which counts that colour over the cubes' choice qubits and tests whether the count equals 2.
- Report its qubits, including ancillas, and its GRADING-call CX, next to one QAOA layer's CX for N = 3.
- From that measured piece, give an explicit lower bound for a full oracle (colours × axes × piece, plus uncompute) and label it as a bound, not as a measured count.
- If you skip (b), say so. Do not guess a number.

**Report (`results/round10.json` and the four-sentence note):**
- the tables from (a), including oracle calls;
- if (b) was done, the measured piece and the labelled bound;
- the random-legal baselines.

Make no speedup claim and no hardware run.

**Invariants the test checks first:**
1. The ideal oracle marks exactly the picks that an independent `solves()` brute force finds, and their number equals `count_answers` for each puzzle.
2. With the ideal oracle, the simulated P(solved) after k iterations equals sin²((2k+1)θ), where sin²θ = M / 6^N, to within 1e-9 for every reported k.
3. Every number in the report recomputes from the saved data. The QAOA comparison values are read from `round6.json` / `round7.json`, not typed in.
4. If (b) is done, the piece circuit gives the right yes/no answer on every one-hot input for its cube/colour/axis, checked by simulating each input.

**Timing:** this must finish by about 14:20. If (a) runs long, drop (b).
