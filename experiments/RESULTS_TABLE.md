# Results Table: All Rounds

In the format of `GRADING.md`, one row per experiment. Every number comes
from `experiments/results/roundN.json` (round 0 from `solution.ipynb`'s
saved outputs; the "ported" row from the notebook after porting).

**How to read the columns**
- **Two-qubit gates / depth:** `transpile(qc, basis_gates=["rz","sx","x","cx"])`
  at the default level (the GRADING call). Depth varies by 1–2 between runs
  because that call sets no seed.
- **P(correct tower):** the fraction of shots that decode to a tower passing
  `solves`. Rows marked **exact** have no shots: they are the exact
  probability from simulating the legal subspace, which has been checked to
  match the real circuit to about 1e-16. Rows marked [min–max] give the
  median over training seeds.
- **Random-guess baseline:** the probability that a uniformly random
  bitstring of the encoding is a solved tower (answers / 2^qubits). A random
  *legal* pick (one choice per cube) is also listed below the table, because
  the circuit only produces legal picks.
- **Device / job ID:** rows marked SV1 or QPU ran on qBraid and carry their
  job ID. All other rows are local simulation and have no job ID.

Encoding for every row: 6 qubits per cube, one-hot over the 6 legal
(front/back, left/right) choices; W-state start; XY mixer. Unless the row
says otherwise: full mixer (15 pairs per cube) and p = 7.

| Round | Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots | P(correct tower) | Random-guess baseline | qBraid job ID |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 4 | Full H (265 ZZ), average-cost training (team notebook) | local Aer (statevector) | 24 | 4590 | 1683 | 1000 | 25.5% (exact 26.35%) | 1.2e-7 | — |
| 1 | 4 | Same as round 0, student's saved angles | local Aer (statevector) | 24 | 4590 | 1684 | 1000 | 25.3% (exact 26.25%) | 1.2e-7 | — |
| 2 | 4 | Reduced H, reference 0 (94 ZZ), same angles | local exact | 24 | 2196 | 974 | — | 26.25% exact (unchanged) | 1.2e-7 | — |
| 2 | 4 | Reduced H, per-pair reference (77 ZZ), same angles | local exact | 24 | 1958 | 911 | — | 26.25% exact (unchanged) | 1.2e-7 | — |
| 3 | 4 | Reduced H, full mixer, average cost, 5 seeds | local exact | 24 | 1958 | 914 | — | 26.37% exact [26.29–26.48] | 1.2e-7 | — |
| 3 | 4 | Reduced H, **ring** mixer (6 pairs), average cost, 5 seeds | local exact | 24 | 1454 | 760 | — | 7.67% exact [7.65–7.67] | 1.2e-7 | — |
| 4 | 4 | Reduced H, full mixer, **Gibbs** training, 5 seeds | local exact | 24 | 1958 | 907 | — | **35.12% exact [35.11–35.12]** | 1.2e-7 | — |
| 4 | 4 | Round-4 circuit as ported into `solution.ipynb` | local Aer (statevector) | 24 | 1958 | 907 | 1000 | **34.3%** (exact 35.12%) | 1.2e-7 | — |
| 5 | 5 (`make_puzzle(5, 16)`) | Round-4 recipe, 3 seeds | local exact | 30 | 3354 | 1147 | — | 9.33% exact [9.33–9.33] | 1.9e-9 | — |
| 6 | 4 | Round-4 recipe, **p = 1**, 3 seeds | local exact | 24 | 314 | 180 | — | 1.14% exact | 1.2e-7 | — |
| 6 | 4 | p = 2 | local exact | 24 | 588 | 297 | — | 2.85% exact | 1.2e-7 | — |
| 6 | 4 | p = 3 | local exact | 24 | 862 | 425 | — | 6.34% exact | 1.2e-7 | — |
| 6 | 4 | p = 4 | local exact | 24 | 1136 | 551 | — | 12.00% exact | 1.2e-7 | — |
| 6 | 4 | p = 5 | local exact | 24 | 1410 | 666 | — | 20.29% exact | 1.2e-7 | — |
| 6 | 4 | p = 6 | local exact | 24 | 1684 | 792 | — | 27.39% exact | 1.2e-7 | — |
| 6 | 4 | p = 7 | local exact | 24 | 1958 | 920 | — | 35.12% exact | 1.2e-7 | — |
| 6 | 4 | p = 8 | local exact | 24 | 2232 | 1038 | — | 41.83% exact | 1.2e-7 | — |
| 6 | 4 | p = 9 | local exact | 24 | 2506 | 1168 | — | 48.52% exact | 1.2e-7 | — |
| 6 | 4 | p = 10 | local exact | 24 | 2780 | 1286 | — | 55.19% exact | 1.2e-7 | — |
| 7 | 3 (`make_puzzle(3, 0)`, 16 answers) | Round-4 recipe, p = 1, noiseless | local Aer | 18 | 200 | 161 | 2000 | 36.95% (exact 36.38%) | 6.1e-5 | — |
| 7 | 3 | p = 1, **assumed noise** | local Aer + noise model | 18 | 200 | 161 | 2000 | 4.75% (27.2% after keeping one-hot shots, 95/349) | 6.1e-5 | — |
| 7 | 3 | p = 2, noiseless | local Aer | 18 | 370 | 282 | 2000 | 63.05% (exact 61.58%) | 6.1e-5 | — |
| 7 | 3 | p = 2, assumed noise | local Aer + noise model | 18 | 370 | 282 | 2000 | 2.15% (32.8% after keeping one-hot shots, 43/131) | 6.1e-5 | — |
| 7 | 3 | p = 3, noiseless | local Aer | 18 | 540 | 397 | 2000 | 74.50% (exact 74.83%) | 6.1e-5 | — |
| 7 | 3 | p = 3, assumed noise | local Aer + noise model | 18 | 540 | 397 | 2000 | 0.65% (22.8% after keeping one-hot shots, 13/57) | 6.1e-5 | — |
| 7 | 3 | p = 4, noiseless | local Aer | 18 | 710 | 519 | 2000 | 82.15% (exact 82.53%) | 6.1e-5 | — |
| 7 | 3 | p = 4, assumed noise | local Aer + noise model | 18 | 710 | 519 | 2000 | 0.30% (18.8% after keeping one-hot shots, 6/32) | 6.1e-5 | — |
| 8 | 3 (`make_puzzle(3, 0)`) | Hardware file `hardware_n3_p1.qasm` (p = 1, after `prepare`), loaded back | local Aer | 19 (18 + marker) | 200 (file holds 215) | 135 | 2000 | 36.95% (exact 36.38%) | 6.1e-5 | — |
| **SV1** | **3** | **Same hardware file, p = 1** | **`aws:aws:sim:sv1`** | **19 (18 + marker)** | **200 (file holds 215)** | **135** | **1000** | **37.70%** (377/1000; all shots one-hot; exact 36.38%) | **6.1e-5** | **`aws:aws:sim:sv1-d8ed-qjob-6ad3b0f638127b44c71ba0d6`** |
| **QPU** | 3 | Same hardware file, p = 1 | `aws:ionq:qpu:forte-enterprise-1` | 19 (18 + marker) | 200 (file holds 215; IonQ recompiles to native gates) | 135 | 100 | _in IonQ queue_ | 6.1e-5 | _pending_ |
| **SV1** | **4** | **Round-4 circuit (reduced H, Gibbs, p = 7), sent from `solution.ipynb`** | **`aws:aws:sim:sv1`** | **25 (24 + marker)** | **1958** | **907** | **1000** | **36.20%** (362/1000; exact 35.12%) | **1.2e-7** | **`aws:aws:sim:sv1-d8ed-qjob-6ad3b20238127b44c71ba11b`** |

**Hardware rows:** P(correct tower) counts all shots, as GRADING.md
defines it. Because noise produces illegal strings, the rows also report
the rate among one-hot shots only, compared with the 7.41% random rate after
the same filter (round 7: the filter alone reaches 7.41%, so that is the
fair comparison).

**Random legal pick** (uniform over one choice per cube, the space the
circuit stays in): N = 4: 2/1296 = 0.154%; N = 5: 2/7776 = 0.026%; N = 3:
16/216 = 7.41%. Under noise this is also the random rate after keeping only
one-hot shots.

**Round 7 noise model** (an assumption, not a device calibration):
depolarizing 1% on `cx`, 0.05% on `sx`/`x`, 2% readout flips, no routing.
Round 7 is accepted, and its test was strengthened after review.

**Classical baseline:** brute force over all orientations takes under 1 s
for N = 4 and 7.4 s for N = 5 (`count_answers`: 0.01 s). No quantum speedup
is claimed.
