# Instant Insanity on a quantum computer

**Team:** Kiarash Naghavi Khanghah, Luis A. Mendez, Hoang Anh Nguyen. **Event:** Qiskit Fall Fest Connecticut 2026, qBraid challenge.
**Level reached:** Warm-up, Core, Bonus.

## Method in one paragraph

A 12-qubit compact encoding (3 qubits per cube: the number 0..5 of the cube's placement, written in binary) searched
two ways. **QAOA** that starts in the equal mix of the 6 valid placements per cube and uses a per-cube mixer that never
leaves them, with an exact 4-local cost Hamiltonian, reaches 98.5 % at 24 rounds (8,648 CX; exact noiseless value,
98.6 +- 0.2 % measured on qBraid SV1). **Grover** with an oracle generated only from the rules (no knowledge of the answer)
reaches 99.85 % at 19 steps (3,987 CX, thanks to an idle qubit the transpiler uses as a clean ancilla; 99.95 +- 0.04 % on
SV1). Random guessing is 0.049 % (any 12-bit string) to 0.15 % (random valid placements). Brute force checks
all 331,776 towers in 0.15 s, and we say so: no speedup is claimed. For the Bonus, the same 24-round angles
trained at N = 4 are reused unchanged on `make_puzzle(n, seed)` with seeds `{5: 16, 6: 86, 7: 68, 8: 4}` (each
checked to have exactly 2 answers with `count_answers`): N = 5: 47.9 % exact (17 qubits, 14,266 CX); N = 6: 36.9 % exact (20 qubits, 22,476 CX); N = 7: 17.1 % exact (23 qubits, 28,142 CX); N = 8: 28.4 % exact (26 qubits, 38,752 CX). On the Rigetti Cepheus-1-108Q QPU the circuits we sent (225, 287 CX) gave 0/500, 0/500 successes, no better than random guessing.

## Results at a glance

"Rounds" and "steps" are circuit depth (QAOA layers, Grover iterations). "Perfect simulator" is the exact success
probability, the best a circuit can do even on a perfect machine: one QAOA round of the warm-up tops out at
18.8 %. Blank = not run there. "Valid readings" is the share of shots where every cube's 3 bits decode to one of its real placements (for the tower, 110 and 111 are impossible): 100 % on a perfect machine, 21.0 % to 27.8 % on the QPU, about what random bits give, so the noise scrambled the state.

| Experiment | Two-qubit gates | Perfect simulator | qBraid SV1 | Rigetti QPU | Random valid placements | Any 12-bit string |
|---|---|---|---|---|---|---|
| 4-cube tower, QAOA 3 rounds (C0) | 1,088 | 4.8 % |  |  | 0.15 % | 0.049 % |
| 4-cube tower, QAOA 12 rounds (C1) | 4,328 | 72.9 % |  |  | 0.15 % | 0.049 % |
| 4-cube tower, QAOA 24 rounds (C2, C2-SV1) | 8,648 | 98.5 % | 98.6 +- 0.2 % |  | 0.15 % | 0.049 % |
| 4-cube tower, Grover 5 steps (G0) | 1,061 | 17.5 % |  |  | 0.15 % | 0.049 % |
| 4-cube tower, Grover 10 steps (G1) | 2,106 | 54.0 % |  |  | 0.15 % | 0.049 % |
| 4-cube tower, Grover 1 step (G1-QPU) | 225 | 1.4 % |  | 0.0 +- 0.0 % (0/500); valid readings 27.8 % | 0.15 % | 0.049 % |
| 4-cube tower, Grover 19 steps (G2, G2-SV1) | 3,987 | 99.85 % | 99.95 +- 0.04 % |  | 0.15 % | 0.049 % |
| 4-cube tower, starter 24-qubit encoding, QAOA 3 rounds (B1) | 940 | 5.2 % |  |  | 0.03 % | 1.2e-05 % (24-bit) |
| Bonus 5-cube tower, QAOA 24 rounds (4-cube angles) (N5, N5-SV1) | 14,266 | 47.9 % | 46.6 +- 1.1 % |  | 0.026 % | 0.0061 % (15-bit) |
| Bonus 5-cube tower, Grover 1 step (G1N5-QPU) | 287 | 0.23 % |  | 0.0 +- 0.0 % (0/500); valid readings 21.0 % | 0.026 % | 0.0061 % (15-bit) |
| Bonus 6-cube tower, QAOA 24 rounds (4-cube angles) (N6) | 22,476 | 36.9 % |  |  | 0.0043 % | 0.00076 % (18-bit) |
| Bonus 7-cube tower, QAOA 24 rounds (4-cube angles) (N7) | 28,142 | 17.1 % |  |  | 0.00071 % | 9.5e-05 % (21-bit) |
| Bonus 8-cube tower, QAOA 24 rounds (4-cube angles) (N8) | 38,752 | 28.4 % |  |  | 0.00012 % | 1.2e-05 % (24-bit) |

## How to run

```bash
pip install -r requirements.txt
pytest -q                                   # offline unit tests (slow ones: pytest -m slow)
jupyter nbconvert --to notebook --execute --inplace solution.ipynb   # about 2 minutes
```

The notebook runs top to bottom in qBraid Lab and is saved with outputs. Switches in its first code cell:
`USE_QBRAID = False` (never submits; `True` would send every row to SV1 and spend credits), `REPLAY_SV1 = True`
(replays the saved SV1 counts, only for the same circuit fingerprint, device and shot count), `RUN_HEAVY = False`
(loads N = 6, 7, 8 from `results/heavy_rows.json`, made by `scripts/run_heavy.py`; `True` recomputes them, about
15 minutes). The submission code accepts only `aws:aws:sim:sv1`, needs a price quote and never prints credentials.
Seed 7 everywhere.

## Results (GRADING format)

From `results/results_table.md`. Every success passed the starter's checks. `-SV1` rows are qBraid SV1 jobs,
`-QPU` rows Rigetti Cepheus-1-108Q jobs; for those the exact value is the noiseless one. Qubits include 2 plumbing
qubits (idle q0 and a top marker that fixes the bit order).

| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|
| 4-cube tower, QAOA 3 rounds (C0): N=4 | compact, 3 qubits per cube, QAOA, legal-move mixer, p=3 | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 14 (12 data + 2 plumbing) | 1,088 | 782 | 4,000 | 0.0473 +- 0.0034 (exact 0.0477) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | none (local run) |
| 4-cube tower, QAOA 12 rounds (C1): N=4 | compact, 3 qubits per cube, QAOA, legal-move mixer, p=12 | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 14 (12 data + 2 plumbing) | 4,328 | 3,095 | 4,000 | 0.7250 +- 0.0071 (exact 0.7294) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | none (local run) |
| 4-cube tower, QAOA 24 rounds (C2): N=4 | compact, 3 qubits per cube, QAOA, legal-move mixer, p=24 | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 14 (12 data + 2 plumbing) | 8,648 | 6,179 | 4,000 | 0.9835 +- 0.0020 (exact 0.9854) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | none (local run) |
| 4-cube tower, QAOA 24 rounds (C2-SV1): N=4 | compact, 3 qubits per cube, QAOA, legal-move mixer, p=24 | aws:aws:sim:sv1 | 14 (12 data + 2 plumbing) | 8,648 | 6,179 | 4,000 | 0.9855 +- 0.0019 (exact 0.9854) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | aws:aws:sim:sv1-5a53-qjob-6ad3ad0838127b44c71b9ff4 (0.375 credits) |
| 4-cube tower, Grover 5 steps (G0): N=4 | compact, 3 qubits per cube, Grover, rules-only oracle, K=5 | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 14 (12 data + 1 idle ancilla (q0) + 1 marker) | 1,061 | 1,550 | 4,000 | 0.1727 +- 0.0060 (exact 0.1755) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | none (local run) |
| 4-cube tower, Grover 10 steps (G1): N=4 | compact, 3 qubits per cube, Grover, rules-only oracle, K=10 | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 14 (12 data + 1 idle ancilla (q0) + 1 marker) | 2,106 | 3,075 | 4,000 | 0.5323 +- 0.0079 (exact 0.5397) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | none (local run) |
| 4-cube tower, Grover 1 step (G1-QPU): N=4 | compact, 3 qubits per cube, Grover, rules-only oracle, K=1 | rigetti:rigetti:qpu:cepheus-1-108q | 14 (12 data + 2 plumbing) | 225 | 330 | 500 | 0.0000 +- 0.0000 (exact 0.0138) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3b05c38127b44c71ba094 (44.7126 credits) |
| 4-cube tower, Grover 19 steps (G2): N=4 | compact, 3 qubits per cube, Grover, rules-only oracle, K=19 | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 14 (12 data + 1 idle ancilla (q0) + 1 marker) | 3,987 | 5,820 | 4,000 | 0.9982 +- 0.0007 (exact 0.9985) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | none (local run) |
| 4-cube tower, Grover 19 steps (G2-SV1): N=4 | compact, 3 qubits per cube, Grover, rules-only oracle, K=19 | aws:aws:sim:sv1 | 14 (12 data + 1 idle ancilla (q0) + 1 marker) | 3,987 | 5,820 | 4,000 | 0.9995 +- 0.0004 (exact 0.9985) | 4.88e-04 (any 12-bit string) / 1.54e-03 (random valid placements) | aws:aws:sim:sv1-5a53-qjob-6ad3ad6c38127b44c71ba006 (0.375 credits) |
| 4-cube tower, starter 24-qubit encoding, QAOA 3 rounds (B1): N=4 | starter one-hot, 6 qubits per cube, QAOA, W x W start + XY mixer, p=3 | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 26 (24 data + 2 plumbing) | 940 | 318 | 4,000 | 0.0548 +- 0.0036 (exact 0.0518) | 1.19e-07 (any 24-bit string) / 3.05e-04 (W x W start subspace) | none (local run) |
| Bonus 5-cube tower, QAOA 24 rounds (4-cube angles) (N5): N=5, make_puzzle(5, 16) | compact, 3 qubits per cube, QAOA p=24, N=4 angles (no retraining) | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 17 (15 data + 2 plumbing) | 14,266 | 10,258 | 2,000 | 0.4845 +- 0.0112 (exact 0.4787) | 6.10e-05 (any 15-bit string) / 2.57e-04 (random valid placements) | none (local run) |
| Bonus 5-cube tower, QAOA 24 rounds (4-cube angles) (N5-SV1): N=5, make_puzzle(5, 16) | compact, 3 qubits per cube, QAOA p=24, N=4 angles (no retraining) | aws:aws:sim:sv1 | 17 (15 data + 2 plumbing) | 14,266 | 10,258 | 2,000 | 0.4660 +- 0.0112 (exact 0.4787) | 6.10e-05 (any 15-bit string) / 2.57e-04 (random valid placements) | aws:aws:sim:sv1-5a53-qjob-6ad3adf038127b44c71ba022 (0.375 credits) |
| Bonus 5-cube tower, Grover 1 step (G1N5-QPU): N=5, make_puzzle(5, 16) | compact, 3 qubits per cube, Grover, rules-only oracle, K=1 | rigetti:rigetti:qpu:cepheus-1-108q | 17 (15 data + 2 plumbing) | 287 | 357 | 500 | 0.0000 +- 0.0000 (exact 0.0023) | 6.10e-05 (any 15-bit string) / 2.57e-04 (random valid placements) | rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3b1b338127b44c71ba0fc (48.7654 credits) |
| Bonus 6-cube tower, QAOA 24 rounds (4-cube angles) (N6): N=6, make_puzzle(6, 86) | compact 3 qubits/cube, Cc QAOA p=24, N=4 angles | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 20 (18 data + 2 plumbing) | 22,476 | 14,001 | 2,000 | 0.3590 +- 0.0107 (exact 0.3690) | 7.63e-06 (any 18-bit string) / 4.29e-05 (random valid placements) | none (local run) |
| Bonus 7-cube tower, QAOA 24 rounds (4-cube angles) (N7): N=7, make_puzzle(7, 68) | compact 3 qubits/cube, Cc QAOA p=24, N=4 angles | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 23 (21 data + 2 plumbing) | 28,142 | 16,032 | 2,000 | 0.1585 +- 0.0082 (exact 0.1710) | 9.54e-07 (any 21-bit string) / 7.14e-06 (random valid placements) | none (local run) |
| Bonus 8-cube tower, QAOA 24 rounds (4-cube angles) (N8): N=8, make_puzzle(8, 4) | compact 3 qubits/cube, Cc QAOA p=24, N=4 angles | local AerSimulator (qiskit-aer 0.17.2, seed 7) | 26 (24 data + 2 plumbing) | 38,752 | 24,245 | 2,000 | 0.2830 +- 0.0101 (exact 0.2841) | 1.19e-07 (any 24-bit string) / 1.19e-06 (random valid placements) | none (local run) |

QAOA 24 rounds (8,648 gates) was rejected by the QPU; the warm-up QAOA 1 round also gave 0/500. The warm-up and the variants C3-C5 are in the notebook and `results/results_table_all.md`.

## qBraid job IDs

| Code | Experiment | Device | Shots | Status | Cost (credits) | qBraid job ID |
|---|---|---|---|---|---|---|
| C2 | 4-cube tower, QAOA 24 rounds | `aws:aws:sim:sv1` | 4,000 | COMPLETED | 0.375 | `aws:aws:sim:sv1-5a53-qjob-6ad3ad0838127b44c71b9ff4` |
| G2 | 4-cube tower, Grover 19 steps | `aws:aws:sim:sv1` | 4,000 | COMPLETED | 0.375 | `aws:aws:sim:sv1-5a53-qjob-6ad3ad6c38127b44c71ba006` |
| W1 | 4-cube warm-up (front/back only), QAOA 2 rounds | `aws:aws:sim:sv1` | 4,000 | COMPLETED | 0.375 | `aws:aws:sim:sv1-5a53-qjob-6ad3adc738127b44c71ba019` |
| N5 | Bonus 5-cube tower, QAOA 24 rounds (4-cube angles) | `aws:aws:sim:sv1` | 2,000 | COMPLETED | 0.375 | `aws:aws:sim:sv1-5a53-qjob-6ad3adf038127b44c71ba022` |
| W1p1 | 4-cube warm-up (front/back only), QAOA 1 round | `rigetti:rigetti:qpu:cepheus-1-108q` | 500 | COMPLETED | 42.3102 | `rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3ae8a38127b44c71ba037` |
| G1 | 4-cube tower, Grover 1 step | `rigetti:rigetti:qpu:cepheus-1-108q` | 500 | FAILED | 0 | `rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3af3a38127b44c71ba052` |
| G1 | 4-cube tower, Grover 1 step | `rigetti:rigetti:qpu:cepheus-1-108q` | 500 | COMPLETED | 44.7126 | `rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3b05c38127b44c71ba094` |
| G1N5 | Bonus 5-cube tower, Grover 1 step | `rigetti:rigetti:qpu:cepheus-1-108q` | 500 | COMPLETED | 48.7654 | `rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3b1b338127b44c71ba0fc` |
| C2 | 4-cube tower, QAOA 24 rounds | `rigetti:rigetti:qpu:cepheus-1-108q` | 500 | FAILED | 0 | `rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3b31438127b44c71ba19a` |
| G2 | 4-cube tower, Grover 19 steps | `rigetti:rigetti:qpu:cepheus-1-108q` | 500 | submitted, result pending |  | `rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3b81b38127b44c71ba4f0` |
| N5 | Bonus 5-cube tower, QAOA 24 rounds (4-cube angles) | `rigetti:rigetti:qpu:cepheus-1-108q` | 500 | submitted, result pending |  | `rigetti:rigetti:qpu:cepheus-1-108q-5a53-qjob-6ad3bc769a9bc182de9c4804` |

Total charged: 1.5 credits on SV1, 135.788 on the QPU (from `results/jobs.json`). Counts are in `results/sv1_counts/` and `results/qpu_counts/`; the notebook only replays them, so re-running it costs nothing. A FAILED job returned no counts and has no row.

## Verified / not verified

**Verified:** every reported tower by `solves(tower_from(...))`; brute force 8 of 331,776 towers;
2 graph-level answers = `count_answers` on every instance (N = 4..8); the starter cost has exactly 2 zeros
among 6,561 candidates; our Hamiltonian equals the classical cost on all 1,296 valid placements and has exactly
2 zeros among all 4,096 strings; decoders on known answer strings in both bit orders; the marker trap of
the one-sided marker shown and fixed; the cost step equals `PauliEvolutionGate`; the mixer never leaves the legal
codes; sampled success rates agree with the exact ones within about two standard errors.
**Not verified:** SV1 for the rows without an `-SV1` twin; hardware behaviour beyond the `-QPU` rows; Grover for N >= 6 (resource estimate only); gate counts on
Qiskit 1.3 (all counts are from qiskit 2.6.0). On Qiskit 1.3.3 (checked locally) `src/` imports and the QAOA code
is unchanged, but `PhaseOracleGate` does not exist there, so the Grover oracle falls back to a diagonal gate built from
the same rule: it marks the same states (tested) and its gate count is not comparable, so it is not reported.

## Honesty

The QAOA angles are trained by a classical simulation of the 6^4 legal cases, which is more work than checking them
directly; rows C3 and the Bonus rows show the circuit still works with angles that never saw the puzzle (C5 does not
count as that: its two ramp numbers were tuned on this puzzle). Grover
uses M = 2 from the classical `count_answers` (with unknown M one would use the BBHT schedule or quantum counting).
No quantum speedup is claimed. Thousands of CX gates are noiseless on SV1, but simulation time still costs credits
(7.5 per minute), and such circuits would not survive today's noisy hardware; the hardware rows above show what
noise already does to a few hundred CX.

## AI use

Claude Code (Anthropic) agents wrote the research notes, the code in `src/`, the tests in `tests/`, the notebook and
these documents, from a plan the team reviewed; the team reviewed, ran and presents everything. Who did what: all three, design, review and presentation; code drafted with AI agents (this note). An external code review (OpenAI Codex) found 12 issues, which were fixed and re-tested (cache fingerprint,
Qiskit 1.3 fallback, same-colour pairs in the oracle, honest C5 wording).
How we kept the agents correct: brute force against the encoding (8 towers), the Hamiltonian against the classical
cost on every candidate, known-answer bitstrings in both bit orders, every reported tower re-checked with
`solves(tower_from(...))`, `pytest` (125 tests) and a headless run of the whole notebook. Every measured number in
this README is generated from `results/results.json` and `results/facts.json`, not typed by hand.

## Crib for questions

* **Encoding:** code k = 0..5 per cube is (front/back pair, left/right pair) = `CHOICES[k]`, on qubits 3c..3c+2, lowest bit first; codes 6, 7 are illegal.
* **Mixer:** per cube, a reflection about the equal mix of its 6 valid placements; it only moves amplitude between them.
* **Why 4-local:** "cube c's chosen pair on this side contains colour k" is a 3-bit function; choosing its values on the unused codes 6, 7 makes it at most 2-local, and squaring the degree count multiplies two of them, so at most 4 Z's per term.
* **Oracle:** for each side and colour, "the colour appears exactly twice on the chosen pairs" (a same-colour pair such as BB counts twice); AND of all of them, built from the cube list only.
* **K formula:** K is the better of the two integers around pi / (4 theta) - 1/2 with sin(theta) = sqrt(M / 6^N); M = 2 gives K = 19 at N = 4.
* **Transfer:** the angles trained once at N = 4 are reused unchanged for N = 5..8.

Files: `solution.ipynb` (main notebook), `src/` (modules), `tests/`, `scripts/run_heavy.py`, `scripts/run_sv1.py`,
`scripts/run_qpu.py`, `slides.pdf` (exported from `presentation/index.html`; download the repo and open that file in a browser to present; GitHub shows HTML as source code, so to view it online use [this rendered link](https://htmlpreview.github.io/?https://github.com/hoanganh-2704/CEadify_QAOA/blob/kiarash/presentation/index.html)),
`results/`, `resources/` (verbatim copy of the starter's helpers).
