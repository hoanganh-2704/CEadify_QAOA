# Round 9 note: noise-grid prediction for the submitted file

1. The only change is a runner that loads the submitted file `results/hardware_n3_p1.qasm` as-is, checking that its SHA-256 equals round 8's `a666efe3…ce515e`. It simulates the file's 215 CX and its marker on q[18] with no re-transpiling, under a grid of noise levels, and passes every counts dict through `results_row(..., marker=True)`, the same pipeline the hardware counts will go through.
2. The checks are right because the prediction is only worth something if it is about the circuit the device receives and if the arithmetic can be redone. So the test requires the hash to match round 8 and the file to hold 215 CX. It requires the noise-off run to sit within 3 sigma of the exact 36.38% with every shot one-hot and no marker drops. And it recomputes every rate, expected 100-shot count, 95% interval and p-value from the saved counts.
3. I wrote `experiments/tests_round9.py` first and ran `.venv\Scripts\python.exe -m pytest experiments/tests_round9.py -q -p no:cacheprovider` (red), then `.venv\Scripts\python.exe experiments/run_round.py 9` (about 9 minutes), then the round-9 tests and the full suite (green).
4. Expected results for a 100-shot run:
   - Noise off: about 37 solved, all 100 shots kept.
   - Under the grid, between about 51 kept / 17 solved (cx 0.3%, readout 0.5%) and 18 kept / 5 solved (cx 1%, readout 2%).
   - At the expected counts, the one-sided p-value against the 7.41% post-selected random rate goes from 8e-8 to 0.008.
   - The 95% intervals of the noisiest cells reach down to 1–2 solved out of 11–14 kept, which would not beat random. So a bad draw at high noise can come out inconclusive.

**Deviation from the assignment:** I simulated **1000 shots per grid point instead of 2000**. One noisy 200-shot run of the 19-qubit file took 19.7 s, so 6 × 2000 shots would have taken about 20 minutes, against a 10-minute budget. At 1000 shots, each simulated rate has its own sampling error of up to about 1.6 points (the kept fraction near 50%), which is small next to the 100-shot intervals below. Seeds were fixed (`seed_simulator = 7`).

**Stated assumptions (a band, not a model of the device):**
- Depolarizing error on cx (grid) and on sx/x (5e-4).
- None on rz.
- Symmetric readout error (grid).
- No routing, since the device is all-to-all.

IonQ recompiles the circuit into its own native gates, so the gate-level noise it actually sees is not this model. The grid only brackets plausible outcomes.

Red pytest line (before implementing, tests_round9.py only):
`4 errors in 5.28s`

Green pytest lines (after implementing):
- `experiments/tests_round9.py`: `4 passed in 3.98s`
- Full suite (`experiments/tests_quantum.py ... experiments/tests_round9.py tests`): `121 passed in 73.13s`

## Grid (submitted 215-CX file, 1000 simulated shots each, scaled to 100 shots; random post-selected rate 7.41%)

| cx error | readout | all-shot P | kept fraction | post-selected P | 100 shots: expected kept [95%] | expected solved [95%] | p-value vs 7.41% |
|---|---|---|---|---|---|---|---|
| 0 | 0 | 36.80% | 100.0% | 36.80% | 100 [100, 100] | 36.8 [27, 46] | 4.6e-17 |
| 0.3% | 0.5% | 17.20% | 50.9% | 33.79% | 50.9 [41, 61] | 17.2 [10, 25] | 7.7e-08 |
| 0.3% | 2% | 12.50% | 39.3% | 31.81% | 39.3 [30, 49] | 12.5 [6, 19] | 1.6e-05 |
| 0.5% | 0.5% | 13.00% | 39.3% | 33.08% | 39.3 [30, 49] | 13.0 [7, 20] | 2.6e-06 |
| 0.5% | 2% | 9.30% | 30.3% | 30.69% | 30.3 [22, 39] | 9.3 [4, 15] | 2.3e-04 |
| 1% | 0.5% | 6.10% | 22.3% | 27.35% | 22.3 [14, 31] | 6.1 [2, 11] | 4.4e-03 |
| 1% | 2% | 5.00% | 18.0% | 27.78% | 18.0 [11, 26] | 5.0 [1, 10] | 8.4e-03 |

"Kept" means a one-hot shot whose marker read 1. A marker flip removes the shot. The intervals are central 95% binomial intervals at the simulated rates. The p-value is P(X ≥ solved | kept, 7.41%) at the rounded expected counts.

**Course question (200 or 215 CX in the README row):** The README row should say 200, because GRADING.md counts every team's circuit with the same `transpile(qc, basis_gates=["rz","sx","x","cx"])` call, and a note should add that the file actually sent holds 215 because `prepare` transpiles at level 1. Neither number is what IonQ executes, since it recompiles into its own native gates anyway.

## Test edit after the red run (diff)

```diff
-SHOTS, N_PRED, BASELINE = 2000, 100, 16 / 216
+MIN_SHOTS, N_PRED, BASELINE = 1000, 100, 16 / 216   # assignment said 2000; see shots_note
-    assert data["shots"] == SHOTS and data["seed_simulator"] == 7
+    assert data["shots"] >= MIN_SHOTS and data["shots_note"] and data["seed_simulator"] == 7
-    sigma = math.sqrt(exact * (1 - exact) / SHOTS)
+    shots = data["shots"]
+    sigma = math.sqrt(exact * (1 - exact) / shots)
-    assert row["kept"] == SHOTS and row["marker_dropped"] == 0
+    assert row["kept"] == shots and row["marker_dropped"] == 0
-        assert shots == SHOTS
+        assert shots == data["shots"]
```
