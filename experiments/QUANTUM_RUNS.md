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

## Planned jobs

| Order | Device | Pricing (from qBraid, read-only query) | Status |
|---|---|---|---|
| 1 | `aws:aws:sim:sv1` | 7.5 credits/min; queue 0 | Approved by the team; waiting on `submit_job` |
| 2 | `aws:ionq:qpu:forte-enterprise-1` (36 qubits, all-to-all connectivity) | 30 credits/task + 8 credits/shot (100 shots = 830 credits ≈ $8.30); queue 5 | Device chosen by the team; p and shots decided after round 7 |
| — | `rigetti:rigetti:qpu:cepheus-1-108q` | 12,000 credits/min (≈ $120/min) | Considered and set aside: time-billed, and its nearest-neighbour wiring adds SWAPs |

## Run log

| # | Date / time | Device | p | Qubits | CX after device transpile | Shots | Job ID | Credits | Valid one-hot shots | Solved towers | P(solved) | vs prediction |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | | | | |

## What each run changed

<!-- One short entry per run: what we expected, what we measured, the gap, and
what we changed or concluded because of it. -->

_No runs yet._ `submit_job` in `solution.ipynb` is still the team's to write.
