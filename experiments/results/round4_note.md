# Round 4 note: training objective

1. The only change is the training objective: instead of the average cost, COBYLA now minimizes the Gibbs score -log(sum over states of p(x) exp(-C(x))) with eta = 1, and the full mixer, the per-pair reduced Hamiltonian, p=7, the p=1 grid start and N(0, 0.05) jitter with seeds 0 to 4 are all unchanged from round 3.
2. The check is right because the new objective must be something we could compute from measured shots without knowing the answer, so my tests build it from a cost histogram of counts, show that two different sets of shots with the same cost histogram score the same, and check that the function never takes a solved list; the second half recomputes every reported P(solved) from its saved angles so no number in the table is copied by hand.
3. I wrote `experiments/tests_round4.py` first and ran `.venv\Scripts\python.exe -m pytest experiments/tests_round4.py -q -p no:cacheprovider` before implementing, then ran `.venv\Scripts\python.exe experiments/run_round.py 4`, then the full suite.
4. Across seeds 0 to 4 the Gibbs objective gave exact P(solved) of 35.12%, 35.11%, 35.12%, 35.12% and 35.12% (median 35.12%, min 35.11%, max 35.12%) with 1958 CX and depth 907 from `transpile(qc, basis_gates=["rz","sx","x","cx"])`, next to the accepted round-3 average-cost spread of 26.37% [26.29, 26.48] on the same circuit shape, while the average cost of the final state went up from about 2.12 to about 2.73.

No Aer run was made this round, so there are no shot rates here.

Red pytest line (before implementing, tests_round4.py only):
`5 failed, 2 errors in 3.21s`

Green pytest lines (after implementing):
- `experiments/tests_round4.py`: `7 passed in 2.30s`
- Full suite (`experiments/tests_quantum.py experiments/tests_round2_review.py experiments/tests_round3_review.py experiments/tests_round4.py tests`): `81 passed in 40.81s`

## Course question: where do the constraints live now?

The W state and the XY mixer already enforce the per-cube rules. Each cube has exactly one 1 in its block of 6 qubits, so it picks exactly one front/back pair and one different left/right pair, because the 6 choices are exactly the ordered pairs of two distinct pairs. The starter QUBO's one-hot penalties and its "same pair on both axes" penalty have nothing left to do.

What is still in the cost Hamiltonian is the colour rule on both axes: on the front/back axis every colour must be used exactly twice, and the same on the left/right axis, scored as the sum of (degree - 2)^2.

That remaining cost is all penalty, not a real objective. The puzzle is a yes/no constraint problem. Every solved tower scores 0, and there is nothing to rank between them. Over the 1,296 legal picks the costs are 0 (2 picks), 2 (60), 4 (288), and so on up to 20. So what training really has to do is push weight out of the large cost-2 and cost-4 shells, which sit just above the answers, into cost 0. That is why an objective that weights cost 0 much more than cost 2 helps P(solved) even though it makes the average cost worse.
