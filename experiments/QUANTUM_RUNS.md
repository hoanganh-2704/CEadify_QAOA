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

## Planned jobs

| Order | Device | Pricing (from qBraid, read-only query) | Status |
|---|---|---|---|
| 1a | `aws:aws:sim:sv1`: N = 4, p = 7, 1000 shots (main result) | 7.5 credits/min; queue 0 | Approved by the team; waiting on `submit_job` |
| 1b | `aws:aws:sim:sv1`: N = 3 `make_puzzle(3, 0)`, p = 1, 1000 shots (the SV1 row to sit next to the IonQ row) | same | Approved by the team ("run it both in SV1 and then the QPU"); waiting on `submit_job` |
| 2 | `aws:ionq:qpu:forte-enterprise-1` (36 qubits, all-to-all connectivity): N = 3, p = 1, the round-8 verified circuit, **100 shots** | 30 + 8 × 100 = **830 credits (≈ $8.30)**; queue 5 | **Approved by the team: 100 shots.** Runs after the SV1 jobs succeed; waiting on `submit_job` |
| — | `rigetti:rigetti:qpu:cepheus-1-108q` | 12,000 credits/min (≈ $120/min) | Considered and set aside: time-billed, and its nearest-neighbour wiring adds SWAPs |

## Run log

| # | Date / time | Device | p | Qubits | CX after device transpile | Shots | Job ID | Credits | Valid one-hot shots | Solved towers | P(solved) | vs prediction |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2 | 2026-10-17 | `aws:aws:sim:sv1` | 1 (N = 3, `make_puzzle(3, 0)`) | 19 (18 + marker) | 200 (GRADING); file holds 215 | 1000 | `aws:aws:sim:sv1-d8ed-qjob-6ad3b0f638127b44c71ba0d6` | _see qBraid jobs page_ | 1000/1000 (marker dropped 0) | 377 | **37.70%** (random post-selected 7.41%) | exact 36.38%; +1.3 pts, within 1σ (±1.5) ✅ |

Raw counts and the full row: `results/qbraid_sv1_n3_p1.json`. Circuit:
`results/hardware_n3_p1.qasm` (SHA-256 checked before sending).

## What each run changed

<!-- One short entry per run: what we expected, what we measured, the gap, and
what we changed or concluded because of it. -->

**Run 2 (SV1, N = 3, p = 1).** Expected 36.4% ± 1.5; measured 37.7%. The
whole path (QASM file → `submit_job` → SV1 → `split_marker` → decode →
`solves`) works on a real qBraid job, and every shot is a legal one-hot
pick, as the W state and XY mixer guarantee. Nothing changed; this is the
noiseless reference row for the IonQ job.

Setup changes before the runs: `submit_job` was written by Claude Code at
the team's request (disclose it in the AI use note). The first two attempts
failed authentication (the key saved on the machine had been rejected);
nothing was sent. They succeeded after the team supplied a new key.
