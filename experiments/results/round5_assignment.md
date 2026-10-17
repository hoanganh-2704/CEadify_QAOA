# Round 5 assignment (one change: the same recipe on N = 5)

**Question:** if you change nothing in the accepted recipe (one-hot W state, full XY mixer, reduced Hamiltonian, Gibbs eta = 1, p = 7, layer-by-layer COBYLA), what does it give on the 5-cube bonus puzzle `make_puzzle(5, 16)`? At 30 qubits this is the largest size that fits the 34-qubit SV1 limit. How do qubits, the GRADING-call CX and depth, and P(solved) grow from N = 4 to N = 5, and how does P(solved) compare with the random-legal baseline and with brute force at that size?

**Write the test first.** It must check these invariants:
1. For the N = 5 puzzle, the set of cost-zero legal picks equals the set that an independent `solves()` brute force finds, and its size matches `count_answers`.
2. The N = 5 Hamiltonian's energy equals the cost tensor on all 6^5 legal picks.
3. Every reported P(solved) recomputes from its stored angles.
4. All runs use the same seeds, with median/min/max computed from those runs.

**Report** (`results/round5.json` and a four-sentence `round5_note.md`):
- seeds 0, 1, 2 (3 seeds, to fit about 10 minutes);
- exact P(solved) median/min/max;
- qubits, CX and depth from the GRADING call;
- random-legal and random-bitstring baselines;
- brute-force time;
- training time per seed.

Do not run Aer at 30 qubits. A full statevector needs about 16 GB, so report exact subspace numbers only and label them that way. Do not retrain N = 4, do not tune anything for N = 5, and claim no speedup. If 3 seeds do not fit in time, report the seeds that finished, and treat an inconclusive result as a finished round.
