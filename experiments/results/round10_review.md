# Round 10 review (Grover with an ideal oracle vs QAOA, legal subspace): final round

- **Verdict:** accept. The scope cut was written before the test, as asked. Part (a) is correct: N = 3 peaks at k = 2 (96.34%) and N = 4 at k = 19 (99.85%). Both tables are generated from `round10.json`, and the earlier hand-typed errors were caught and regenerated. The note says plainly that best k uses M, that there is no oracle gate count, and that no speedup is claimed. It never says Grover is cheaper. One caution remains. The "per round" table is tilted toward Grover: an ideal-oracle call is free, while a QAOA layer is charged its full 170–274 CX. A real oracle has to compute the colour degrees reversibly, compare them with 2, and uncompute, which is at least the information one cost layer carries plus ancillas. So the column showing QAOA CX with no Grover CX next to it must not be read as a cost comparison. Add one caption line saying so.
- **Invariant and pytest line:**
  - The oracle marks exactly the answers from the `solves()` brute force, and their number equals `count_answers`.
  - P(solved) equals sin²((2k+1)θ) to 1e-9.
  - The QAOA values are read from `round6.json` and `round7.json`.

  My run printed `experiments/tests_round10.py: 6 passed in 3.14s`.
- **Course question:** answered for Grover's speedup. It is provable and quadratic in oracle queries, it needs M (or an exponential-search or quantum-counting schedule), and it says nothing about gate cost or noise. Every member should also be able to say that k = 19 iterations at N = 4 is a far deeper circuit than anything that survived the round-7/9 noise study.
- **One sentence for the presentation:** "With a free, perfect oracle and the answer count known, Grover reaches 96–100%, but each Grover step needs a reversible check of the colour rule that we did not build and that costs at least a QAOA layer, so we show it as a reference curve, not as a cheaper method, and we claim no speedup for either."
- **What I refused to do:** credit Grover with a gate count nobody measured, rank the two methods on cost, or reopen part (b) after the deadline.
