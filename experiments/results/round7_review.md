# Round 7 review (stated noise model, make_puzzle(3, 0))

- **Verdict:** accept the data, with two fixes to the test. Under the assumed noise (cx 1e-2, sx/x 5e-4, readout 2%, no routing), the all-shot rate falls below the 7.41% random-legal rate from p = 1 on. Post-selection on one-hot keeps it above random (27.2% at p = 1, from 349 kept shots), but at p ≥ 3 only a few dozen shots survive. Dropping p = 6 for time is honest because it is recorded. The test's comment calling the drop "allowed by the assignment" is wrong: the assignment never said that. I could not diff the removed "no-op" line, because the red version was never committed. That edit cannot be verified, so do not repeat it: edits to a test after a red run go in the note as a diff.
- **Invariant and pytest line:** with noise off, Aer matches exact within 3σ with 100% one-hot. The post-selected count equals the one-hot count, and every rate recomputes from the saved counts with `solves()`. My run printed `experiments/tests_round7.py: 7 passed in 3.59s`. Two weaknesses:
  - `p_values + dropped_p == P_VALUES` passes when *every* p is dropped (rows empty, so every loop is vacuous). Require at least p = 1 and 2.
  - `test_noise_model_has_the_stated_errors` checks the gate names, not the error rates.
- **Course question owed:** this instance has 16 answers out of 216, so it is an easy target with a high random baseline. Can each member explain why a hardware result must be compared with the post-selected random rate (7.41%) and not the random-bitstring rate (6.1e-5)?
- **Recommendation for the IonQ job (the team decides):**
  - **Run:** N = 3 `make_puzzle(3, 0)`, p = 1 (200 CX, all-to-all so no routing), 200 shots, post-select one-hot, check every kept shot with `solves()`. It costs 30 + 8 × 200 = 1630 credits. Run the identical circuit on SV1 first.
  - **Expected under our pessimistic model:** about 35 kept shots and about 10 solved, against about 2.6 for random. The one-sided binomial p-value is about 2e-4. At 100 shots (830 credits) that becomes about 17 kept and 5 solved, p about 7e-3.
  - **Do not use** N = 4 p = 1 (about 0.5 solved expected in 200 shots, indistinguishable from random) or p = 2 (fewer kept shots and weaker evidence).
  - **Present** it as one measured run on one easy instance, not as a hardware claim.
- **What I refused to do:** submit any job, call qBraid, approve hardware spending, or retrain.
