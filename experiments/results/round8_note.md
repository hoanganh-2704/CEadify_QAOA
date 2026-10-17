# Round 8 note: freezing the hardware circuit and its readout pipeline

1. The only change is new code that builds the N = 3 `make_puzzle(3, 0)`, p = 1 circuit from the saved round-7 angles and writes it to `results/hardware_n3_p1.qasm`, plus a `results_row` function that turns any counts dict into the README results-table fields. The build goes through `resources.helpers.prepare`, the same path `submit_job` would get: marker qubit 18 fixed at 1, every qubit measured, transpiled to rz/sx/x/cx. There was no retraining and no new angles.
2. The checks are right because they test the file itself, not the code that made it. Loading the QASM back must give the exact subspace state at the saved angles (overlap 1 to 1e-9, marker at 1, no weight outside one-hot). Its GRADING-call CX count must equal round 7's p = 1 value. Hand-made counts must decode with qubit 0 rightmost. Noiseless Aer on the loaded file must sit within 3 sigma of exact. And round 7's saved noisy counts must reproduce the saved row through the new function.
3. I wrote `experiments/tests_round8.py` first and ran `.venv\Scripts\python.exe -m pytest experiments/tests_round8.py -q -p no:cacheprovider` (red), then `.venv\Scripts\python.exe experiments/run_round.py 8`, then the round-8 tests and the full suite (green).
4. The file is 19 qubits (18 + marker) with SHA-256 `a666efe3ffc5203ba06ef75fd910b7e497f3722e2bd84b30e5d6cb9d64ce515e`. Its GRADING-call count is 200 CX at depth 135, equal to round 7's 200. Noiseless Aer on the loaded file solved 739 of 2000 shots (36.95%, all one-hot, exact 36.38%). The round-7 noisy counts give 95 solved of 2000 (4.75%) and 95 of 349 kept one-hot shots (27.22%), the same as the saved row, against a 7.41% random legal (post-selected) baseline.

**Two things the team should know before submitting (no hardware claim is made here):**
- **The file holds 215 CX, not 200.** `prepare` transpiles at optimization level 1, and the GRADING call (default level) on the same file gives 200. The marker is not the cause: it adds one `x` gate and no CX, and the raw circuit plus the marker through the GRADING call also gives 200. The round-7 noise study simulated the 200-CX version, so the submitted file has 15 more two-qubit gates than the circuit behind the round-7 noisy numbers. The README row should use the GRADING-call 200, as GRADING.md says.
- **`helpers.strip_marker` raises if any shot reads the marker as 0.** With about 2% readout error, roughly 2% of hardware shots will. My `split_marker` drops those shots and counts them in `marker_dropped`. It also decides which end is the marker only when exactly one end reads 1 in at least 90% of shots, and raises otherwise. At these angles qubit 0 (cube 0, choice 0) reads 1 in 23.8% of shots, so the real marker is clear. In a tiny hand-made dict, though, both ends can read 1, and guessing there would decode every shot backwards.

## Table rows from `results_row`

| Puzzle | Encoding | Device | Qubits | CX (GRADING) | Depth (GRADING) | Shots | P(correct tower), all shots | P, one-hot post-selected (solved/kept) | Random baseline (post-selected) |
|---|---|---|---|---|---|---|---|---|---|
| N=3 `make_puzzle(3, 0)` | one-hot 6 per cube + marker | local Aer, noiseless, loaded QASM | 19 | 200 | 135 | 2000 | 36.95% | 36.95% (739/2000) | 7.41% |
| N=3 `make_puzzle(3, 0)` | one-hot 6 per cube | local Aer, round-7 noise model (saved counts, no marker) | 18 | 200 | 161 | 2000 | 4.75% | 27.22% (95/349) | 7.41% |

Job ID: none. Nothing was submitted.

Red pytest line (before implementing, tests_round8.py only):
`6 failed, 3 errors in 3.98s`

Green pytest lines (after implementing):
- `experiments/tests_round8.py`: `10 passed in 13.05s`
- Full suite (`experiments/tests_quantum.py experiments/tests_round2_review.py ... experiments/tests_round8.py tests`): `117 passed in 61.12s`

## Test edits after the red run (diff)

My hand-made counts first used solved picks with cube 0 at choice 0, so qubit 0 also read 1 and both ends of every key were 1. The implementation then correctly reported those dicts as ambiguous. I changed the test data, not the expectation that a clear reversal is undone and an ambiguous one is not guessed:

```diff
 def test_hand_made_counts_decode_with_qiskit_order(cubes):
-    solved, unsolved = solved_and_unsolved(cubes)
-    counts = {key(solved): 5, key(unsolved): 3, "1" + "1" * 18: 2}
+    solved = solved_with_qubit0_off(cubes)
+    unsolved = next(... non-solved pick with cube 0 not at choice 0 ...)
+    counts = {key(solved): 5, key(unsolved): 3, "1" + "0" * 18: 2}   # last: marker only

+def solved_with_qubit0_off(cubes): ...   # a solved pick whose cube 0 is not choice 0

 def test_reversed_keys_are_restored_by_the_marker_or_not_counted(cubes):
-    flipped = S.results_row({key(solved)[::-1]: 4}, cubes, marker=True)
-    assert flipped["solved"] == 4
+    clean = solved_with_qubit0_off(cubes)
+    flipped = S.results_row({key(solved)[::-1]: 4, key(clean)[::-1]: 6}, cubes, marker=True)
+    assert flipped["solved"] == 10

 def test_marker_read_as_zero_is_dropped_not_fatal(cubes):
-    solved, _ = solved_and_unsolved(cubes)
-    counts = {key(solved): 9, "0" + key(solved)[1:]: 1}
+    clean = solved_with_qubit0_off(cubes)
+    counts = {key(clean): 9, "0" + key(clean)[1:]: 1}

+def test_ambiguous_marker_end_raises_instead_of_guessing(cubes): ...   # new
```
