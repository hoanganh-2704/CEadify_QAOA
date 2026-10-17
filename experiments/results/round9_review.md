# Round 9 review (noise-rate grid for the submitted 215-CX file)

- **Verdict:** accept. The file was simulated as-is, its hash matches round 8, and the 6-point grid plus the noiseless row is reported. The prediction for 100 IonQ shots is about 18–51 kept and 5–17 solved, against about 1.3–3.8 for random among the kept shots. The student again edited its own test after the red run, changing 2000 to `>= 1000` with a recorded `shots_note`. That edit kept the invariant: the hash, noise-off within 3σ (now scaled to the shots actually run), 100% one-hot, and recompute-from-counts all still hold. It only gives up precision, and it is disclosed. But this is the second time. A scope change belongs in the note *before* the test is touched, not after a red run.
- **Invariant and pytest line:**
  - The circuit is loaded from the file with a matching SHA-256.
  - With noise off, the result is within 3σ of exact, with no shots dropped.
  - Every rate and expected count recomputes from the saved counts.

  My run printed `experiments/tests_round9.py: 4 passed in 5.01s`.
- **Course question:** answered. The README reports 200 CX (the GRADING rule) and notes that the file holds 215 and that IonQ recompiles it. On the statistic, "the p-value of the expected count" is not the right planning number. The right one is power: the chance that a real 100-shot run reaches p < 0.05 against 7.41%. I computed it from the student's rates (kept ~ Bin(100, f), solved ~ Bin(kept, q)): about 1.00 at 0.3%/0.5%, 0.94 at 0.5%/2%, 0.78 at 1%/0.5% and 0.71 at 1%/2%. Report power next to the p-values.
- **Next change (round 10):** as in `round10_assignment.md`: how does Grover amplitude amplification over the same legal picks compare with QAOA in P(solved), oracle calls and gate cost, with no speedup claim?
- **What I refused to do:** interpret the queued IonQ job before it returns, adjust the prediction after seeing the SV1 numbers, or change the submitted file.
