# Round 3 note: full vs ring XY mixer

1. The only thing I changed is the mixer: the full mixer puts an XX+YY gate on all 15 pairs of each cube's 6 qubits, and the ring mixer uses only the 6 neighbour pairs (0,1), (1,2), ..., (5,0). Everything else stayed the same for both: the per-pair-reference reduced Hamiltonian, the average-cost objective, layer-by-layer COBYLA to p=7 with the round-1 maxiter and rhobeg, and N(0, 0.05) jitter on the p=1 start.
2. A new mixer gives a different landscape, so the saved round-1 angles say nothing about it, and one training run per mixer could just be a lucky or unlucky start. That is why I trained each mixer five times from the same seeds (0 to 4) and compared the spreads instead of single numbers.
3. I ran `.venv\Scripts\python.exe experiments/run_round.py 3`, which trains both mixers, saves every run's seed, angles and P(solved) to results/round3.json, and transpiles each mixer's median-seed circuit with `transpile(qc, basis_gates=["rz","sx","x","cx"])`.
4. The full mixer reached a median exact P(solved) of 26.37% (min 26.29%, max 26.48%) with 1958 CX and depth 914, and the ring mixer reached a median of 7.67% (min 7.65%, max 7.67%) with 1454 CX and depth 760, so the two spreads do not overlap and I am leaving the decision to the review.

No Aer run was made this round, so there are no shot rates in this note.

Pytest summary line, from `.venv\Scripts\python.exe -m pytest experiments/tests_quantum.py experiments/tests_round2_review.py experiments/tests_round3_review.py tests -q -p no:cacheprovider` run after this note was written and before this line was added:

`74 passed in 39.12s`
