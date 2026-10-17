# Round 8 assignment (one change: freeze the hardware circuit and its readout pipeline)

**Question:** is the exact file the team will submit (N = 3 `make_puzzle(3, 0)`, p = 1, the saved round-7 p = 1 angles) the same circuit that produced the round-7 numbers? And does the path from counts dict → decode → one-hot post-selection → `solves()` read a job result correctly, including Qiskit's bit order (qubit 0 rightmost)?

**The one change:** add a function that builds this circuit from the saved angles, measures every qubit, and writes it to a file the team can submit: OpenQASM (`qiskit.qasm2.dumps` or `qasm3`), saved at `results/hardware_n3_p1.qasm`. Add a second function that turns any counts dict into the README results-table fields. No retraining, no new angles, no qBraid calls.

**The test (written first) must check:**
1. **Round trip:** loading the saved QASM back gives the same circuit. With measurements removed, its statevector on the 216 legal states equals the exact subspace state at the saved angles, to 1e-9 up to a global phase, and has no weight outside one-hot.
2. **Gate count:** the GRADING-call CX count of the loaded circuit equals the `cx_grading` stored for p = 1 in `round7.json`.
3. **Bit order:** a hand-made counts dict with a known solved pick, a known unsolved pick and a non-one-hot string gives the right solved/kept/total counts. If the key's bit order is reversed, that same solved pick must not be counted as solved.
4. **Pipeline on simulated counts:** noiseless Aer on the loaded circuit (2000 shots, seed 7) is within 3σ of the exact P(solved) and 100% one-hot. The round-7 noisy p = 1 counts, put through the new function, reproduce the saved round-7 row exactly.

**Report (`results/round8.json` and the four-sentence note):**
- the QASM file's SHA-256;
- qubit count and GRADING-call CX/depth;
- the noiseless and round-7-noisy table rows produced by the new function;
- the random-legal (7.41%) baseline.

Make no hardware claim.
