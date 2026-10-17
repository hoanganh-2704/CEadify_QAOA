# qBraid Runs (SV1 and Hardware)

The record of every job sent through qBraid: what was predicted before the
run, what was measured, and what changed. Entries are added only after a job
finishes. Predictions come from local simulation (`PROGRESS.md`, rounds 4–6).
Measured numbers come only from returned counts.

**Rules followed** (challenge `AGENTS.md`):
- SV1 runs come before any hardware run.
- A hardware job runs only with the team's explicit go-ahead for that device,
  circuit and shot count.
- No API key appears in code, a notebook, an output or a commit.

**Every reported tower is checked** with `solves(tower_of(...))`, decoded
with Qiskit bit order (qubit 0 rightmost) after `strip_marker`.

## Predictions (before any run)

Circuit: N = 4 cubes, reduced Hamiltonian, full XY mixer, Gibbs-trained
angles, plus 1 marker qubit added by `prepare`.

| p | Exact P(solved), noiseless | CX (GRADING transpile) | Predicted on SV1 | Rough QPU estimate P·0.995^CX |
|---|---|---|---|---|
| 1 | 1.14% | 314 | ≈ 1.1% ± 0.3 (1000 shots) | ≈ 0.24% |
| 2 | 2.85% | 588 | ≈ 2.9% ± 0.5 | ≈ 0.15% |
| 7 | 35.12% | 1958 | ≈ 35% ± 1.5 (local Aer gave 34.3%) | ≈ 0.002% (below random) |

Baselines: random legal pick 0.154%; random 24-bit string 1.2 × 10⁻⁷.
The QPU column is a back-of-envelope bound assuming about 99.5% two-qubit
fidelity and no routing overhead. It is not a measurement. Device transpiling
usually adds CX, which makes it worse.

## Prediction for the IonQ job (round 7 + teacher's review)

The round-7 noise study (assumed: 1% `cx` depolarizing, 0.05% `sx`/`x`, 2%
readout, no routing) says the 4-cube circuit cannot show a signal on
hardware even at p = 1: about 0.5 solved shots expected, which can't be told
apart from random. The 3-cube puzzle can:

| Candidate job | Credits | Expected one-hot shots kept | Expected solved | Random would give | Chance random does this well |
|---|---|---|---|---|---|
| **N = 3 `make_puzzle(3, 0)`, p = 1, 200 shots** (teacher's recommendation) | 1630 (≈ $16.30) | ≈ 35 | ≈ 10 | ≈ 2.6 | ≈ 2 × 10⁻⁴ |
| **N = 3, p = 1, 100 shots (chosen)** | 830 (≈ $8.30) | ≈ 17 | ≈ 5 | ≈ 1.3 | ≈ 7 × 10⁻³ |
| N = 4, p = 1, 100 shots | 830 | — | ≈ 0.5 | ≈ 0.5 | indistinguishable |

These are predictions from an assumed noise model, not measurements. IonQ's
real error rates may be better or worse. The comparison is against the
**post-selected random rate (7.41%)**, because we keep only one-hot shots and
a random legal pick of 3 cubes solves 16/216 of the time.

To follow GRADING.md ("add a row for it next to the matching SV1 row"), the
N = 3, p = 1 circuit should also run on SV1, which is cheap.

### Refined prediction for the submitted 215-CX file (round 9, 100 shots)

Simulated with 1000 shots per cell and scaled to 100; 95% intervals. The
1-qubit error is 0.05% throughout.

| CX error | Readout error | Expected kept | Expected solved | p-value vs 7.41% |
|---|---|---|---|---|
| 0 | 0 | 100 [100, 100] | 36.8 [27, 46] | 4.6 × 10⁻¹⁷ |
| 0.3% | 0.5% | 50.9 [41, 61] | 17.2 [10, 25] | 7.7 × 10⁻⁸ |
| 0.3% | 2% | 39.3 [30, 49] | 12.5 [6, 19] | 1.6 × 10⁻⁵ |
| 0.5% | 0.5% | 39.3 [30, 49] | 13.0 [7, 20] | 2.6 × 10⁻⁶ |
| 0.5% | 2% | 30.3 [22, 39] | 9.3 [4, 15] | 2.3 × 10⁻⁴ |
| 1% | 0.5% | 22.3 [14, 31] | 6.1 [2, 11] | 4.4 × 10⁻³ |
| 1% | 2% | 18.0 [11, 26] | 5.0 [1, 10] | 8.4 × 10⁻³ |

**Power** (teacher's round-9 review): the chance a 100-shot run reaches
p < 0.05 against 7.41% is about 1.00 / 0.94 / 0.78 / 0.71 from the best to
the worst assumed noise.

How to read the real result: find the row whose kept/solved range contains
the IonQ counts; that brackets the chip's effective noise. At the noisiest
settings, the low ends of the intervals do not beat random, so an unlucky
run could be inconclusive.

## Planned jobs

| Order | Device | Pricing (from qBraid, read-only query) | Status |
|---|---|---|---|
| 1a | `aws:aws:sim:sv1`: N = 4, p = 7, 1000 shots (main result) | 7.5 credits/min; queue 0 | Approved by the team; waiting on `submit_job` |
| 1b | `aws:aws:sim:sv1`: N = 3 `make_puzzle(3, 0)`, p = 1, 1000 shots (the SV1 row to sit next to the IonQ row) | same | Approved by the team ("run it both in SV1 and then the QPU"); waiting on `submit_job` |
| 2 | `aws:ionq:qpu:forte-enterprise-1` (36 qubits, all-to-all connectivity): N = 3, p = 1, the round-8 verified circuit, **100 shots** | 30 + 8 × 100 = **830 credits (≈ $8.30)**; queue 5 | **Approved by the team: 100 shots.** Runs after the SV1 jobs succeed; waiting on `submit_job` |
| — | `rigetti:rigetti:qpu:cepheus-1-108q` | 12,000 credits/min (≈ $120/min) | Considered and set aside: time-billed, and its nearest-neighbour wiring adds SWAPs |
| 3 | `aws:rigetti:qpu:cepheus-1-108q` (Rigetti via AWS) | 30 credits/task + 0.0425 credits/shot → 1000 shots = **72.5 credits (≈ $0.73)**; queue 1 | **Approved by the team ("use the cheapest QPU"), 1000 shots, sent.** This is the cheapest clearly priced online gate-model QPU in a full read-only price listing; the `openquantum:*` routes list no pricing, so they were avoided. No round-9 prediction covers it, because routing on the grid adds SWAPs, so expect a weaker signal than IonQ. |

## Run log

| # | Date / time | Device | p | Qubits | CX after device transpile | Shots | Job ID | Credits | Valid one-hot shots | Solved towers | P(solved) | vs prediction |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-10-17 | `aws:aws:sim:sv1` | 7 (N = 4) | 25 (24 + marker) | 1958 (GRADING) | 1000 | `aws:aws:sim:sv1-d8ed-qjob-6ad3b20238127b44c71ba11b` | 3.04 | all (`strip_marker` raised no error) | 362 | **36.20%** (random legal 0.154%) | exact 35.12%; +1.1 pts, within 1σ (±1.5) ✅ |
| 2 | 2026-10-17 | `aws:aws:sim:sv1` | 1 (N = 3, `make_puzzle(3, 0)`) | 19 (18 + marker) | 200 (GRADING); file holds 215 | 1000 | `aws:aws:sim:sv1-d8ed-qjob-6ad3b0f638127b44c71ba0d6` | 0.375 | 1000/1000 (marker dropped 0) | 377 | **37.70%** (random post-selected 7.41%) | exact 36.38%; +1.3 pts, within 1σ (±1.5) ✅ |

| 3 | 2026-10-17 | `aws:ionq:qpu:forte-enterprise-1` | 1 (N = 3) | 19 (18 + marker) | IonQ native (recompiled) | 100 | `aws:ionq:qpu:forte-enterprise-1-d8ed-qjob-6ad3b15c38127b44c71ba0ea` | est. 830 (charged on completion) | _queued, position 6_ | | | |

| 4a | 2026-10-17 14:06 | `aws:rigetti:qpu:cepheus-1-108q` (second team account) | 1 (N = 3) | 19 | — | 1000 | `…-8876-qjob-6ad3b90e38127b44c71ba61e` | **0 (failed)** | FAILED: "Job failed to initialize. The compute backend did not return a job identifier." Never ran. | | | |
| 4b | 2026-10-17 | same | 1 (N = 3) | 19 | — | 1000 | `…-8876-qjob-6ad3be589a9bc182de9c48f8` | **0 (failed)** | FAILED: "uses a gate: v which is … not supported by the device". qBraid turns Qiskit's `sx` into Braket's `v`, which this Rigetti route rejects. | | | |
| 4c | 2026-10-17 | same | 1 (N = 3), **`sx` rewritten as `rx(π/2)`** (state verified equal up to global phase; local Aer 739/2000, the same as round 8) | 19 (18 + marker) | 215 in the file sent; Rigetti routing adds SWAPs | 1000 | `aws:rigetti:qpu:cepheus-1-108q-8876-qjob-6ad3bebb9a9bc182de9c48ff` | est. 72.5 | **0 / 937** (63 marker misreads dropped) | 0 | **0.00%** all shots; 0 legal shots to post-select (random post-selected rate 7.41%) | **Fully decohered:** see run 4c below |

Raw counts and the full row: `results/qbraid_sv1_n3_p1.json`. Circuit:
`results/hardware_n3_p1.qasm` (SHA-256 checked before sending).

## What each run changed

<!-- One short entry per run: what we expected, what we measured, the gap, and
what we changed or concluded because of it. -->

**Run 5 (SV1, N = 4, p = 10, the new main result).** The team asked to
raise p. Training p = 100 in time was not possible, and fast shortcuts were
worse: the trained p = 10 angles stretched to p = 100 gave 19–29%, and a
4-parameter linear ramp at p = 100 gave 0.88%. So the notebook moved to the
trained p = 10 angles from round 6 (seed 1; they reproduce with angle
difference 0.0). Expected 55.2% ± 1.6; measured **53.1%** (531/1000),
within 1.3σ. Job `aws:aws:sim:sv1-d8ed-qjob-6ad3bf029a9bc182de9c490f`,
**4.27 credits**, 2780 CX, depth 1286. Classical tests still 32 passed.

**Run 4c (Rigetti Cepheus via AWS, N = 3, p = 1, 1000 shots).** Expected:
weaker than IonQ, because the grid routing adds SWAPs; round 9 did not cover
it. Measured: **0 of 937 shots legal, 0 solved.** Diagnosis from the raw
counts (`results/qbraid_rigetti_n3_p1.json`):
- The marker qubit (one X gate) read 1 in 93.7% of shots, so readout and bit
  order work.
- The 18 data bits have a Hamming-weight distribution centred on 9, with
  999 distinct strings in 1000 shots, which is the signature of uniform
  random bits. A legal string has weight 3, and a bit-order error would not
  change the weight, so this is noise, not a decoding bug.
- Uniform random bits give 6³/2¹⁸ × 937 ≈ 0.8 legal shots expected, so 0
  is exactly what full decoherence predicts.

Conclusion: on this device, after routing, the 215-CX circuit loses all
quantum signal. This is the hardware row next to SV1's 37.7% on the same
file. It is the honest "noise wins" result that rounds 6–7 predicted for
deep circuits on nearest-neighbour hardware.

**Run 1 (SV1, N = 4, p = 7, the main result).** Sent by running
`solution.ipynb` top to bottom (7.3 min), so the job ID and result are saved
in the notebook. Expected 35.1% ± 1.5; measured 36.2% (local Aer gave
34.3%). The improved circuit behaves on SV1 exactly as simulated. This is
the row for the README.

**Run 2 (SV1, N = 3, p = 1).** Expected 36.4% ± 1.5; measured 37.7%. The
whole path (QASM file → `submit_job` → SV1 → `split_marker` → decode →
`solves`) works on a real qBraid job, and every shot is a legal one-hot
pick, as the W state and XY mixer guarantee. Nothing changed; this is the
noiseless reference row for the IonQ job.

Setup changes before the runs: `submit_job` was written by Claude Code at
the team's request (disclose it in the AI use note). The first two attempts
failed authentication (the key saved on the machine had been rejected);
nothing was sent. They succeeded after the team supplied a new key.
