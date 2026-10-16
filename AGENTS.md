# Instructions for AI coding agents

This file is for AI coding agents (Claude Code, GitHub Copilot, Cursor, Codex, the qBraid Lab assistant and others) helping a team solve the Instant Insanity challenge. Humans can read it too: it states the rules an agent should follow so a team's results stay correct and reproducible.

Read `README.md` for the challenge and `GRADING.md` for what the team must hand in. The team owns every decision; you propose, run checks and explain.

## The problem, precisely

- A cube is three **opposite-face pairs**. In the starter notebook a cube is a list of three two-letter strings, for example `["GR", "BR", "GY"]`: green opposite red, blue opposite red, green opposite yellow.
- In a tower, each cube puts one pair on the front/back axis, a different pair on the left/right axis, and hides the third pair on top and bottom. A cube has 24 orientations.
- A tower is **solved** when each of the four sides shows every colour exactly once.
- Equivalent graph form: one node per colour, one edge per opposite pair. A solution is two **2-factors** (edge sets meeting every node exactly twice), one edge per cube in each, that never use the same edge of a cube. Each cube therefore has 6 valid choices: an ordered pair of distinct pair indices.
- The four-cube instance `CUBES` in `starter_notebook.ipynb` has exactly one tower. The brute force finds 8 solved orientations of 331,776 (one tower in its 8 symmetric positions). At the graph level, 2 of the 1,296 cases solve it (the tower and its quarter turn).
- Bonus: N cubes, N colours, the same four-sides rule. `make_puzzle(n, seed)` builds one with a planted answer. Seeds `{5: 16, 6: 86, 7: 68, 8: 4}` give exactly one tower; check any other seed with `count_answers` first.

## Reuse the starter notebook's functions

Define nothing twice. The starter defines or imports these names, and its saved outputs show them working. Names marked *helpers* live in `resources/helpers.py`; import them with `from resources.helpers import ...` from the repo root. In the team's own submission repo, copy `resources/helpers.py` and `resources/__init__.py` into a `resources/` folder beside the notebook, so the same import works.

| Name | What it does |
|---|---|
| `CUBES`, `COLOURS` | The four-cube instance and the colour letters. |
| `orientations(cube)`, `solves(tower)` | The 24 visible-colour views of a cube; the four-sides check. |
| `CHOICES`, `degrees`, `is_two_factor` | The 6 per-cube choices; colour degrees of a pick; the 2-factor test. |
| `front_back`; *helpers:* `orient(cubes, picks)`, `tower_from(cubes, choice)` | The 4 front/back 2-factors; walk a 2-factor into front and back colours; turn a full (front/back, left/right) choice per cube into a tower. |
| `cost(cubes, x, y)` | The QUBO cost: zero exactly for a solved tower (`LAMBDA = MU = 2`). |
| `build_hamiltonian(cubes)` | The 24-qubit one-hot Hamiltonian. Qubit `6c + p` is x[c][p] (front/back), qubit `6c + 3 + p` is y[c][p] (left/right). |
| `energy(H, bits)`; *helpers:* `diagonal(H)` | Evaluate a Z-only Hamiltonian on one bitstring, or on all of them. |
| `front_back_hamiltonian(cubes, lam)` | The 12-qubit warm-up Hamiltonian. Qubit `3c + p` is x[c][p]. |
| `cost_layer(qc, H, gamma)` | exp(-i gamma H) from `rz` and `rzz`, for Hamiltonians of Z and ZZ terms. |
| `w_state`, `xy_mixer`, `constrained_qaoa` | The one-hot-preserving QAOA from the warm-up. |
| *helpers:* `prepare`, `strip_marker`; `run_on_qbraid(circuit, shots)` | Add a marker qubit and transpile; send the circuit with the team's `submit_job`; return counts in Qiskit order. Falls back to local Aer while `submit_job` returns `None`. |
| *helpers:* `solution_strings`, `draw_nets`, `draw_graph`, `draw_tower`, `plot_*`, `show`, `CIRCUIT` | Bitstrings of front/back picks, and the notebook's figures. |
| `make_puzzle(n, seed)`, `count_answers(cubes)` | Bonus puzzle generator and brute-force answer counter. |
| `submit_job(qc, shots)` | A stub the team writes: query a qBraid device, submit the job, return counts. Help the team write it; do not paste a finished version. |

## Rules

### Correctness first

1. **Verify the model classically before any quantum run.** For any new encoding or Hamiltonian, enumerate the candidates (or a large random sample for big N) and confirm: the known answer has the lowest cost, nothing wrong ties with it, and the Hamiltonian value equals the classical cost on every checked bitstring. Show this check in the notebook.
2. **Mind Qiskit bit order.** In a Qiskit counts key, qubit 0 is the **rightmost** character. Decode with that, and test your decoder on a known answer before trusting it.
3. **Check every reported tower** with `solves(tower_from(...))` or an equivalent independent checker. A low energy is not proof.
4. **Report the random-guess baseline** next to every success rate: the chance that a uniform random bitstring of the encoding is a solved tower.
5. **Do not overclaim.** No "quantum advantage" or "speedup" unless the team measured it against a fair classical method. Brute force solves the four-cube puzzle in a fraction of a second; say so.

### Compute and cost

6. **Iterate on the local Aer simulator.** Use `Statevector` or `AerSimulator` with a fixed seed while developing. Submit to SV1 (`aws:aws:sim:sv1`) only for results the team will report.
7. **Know the price.** A small SV1 job costs 0.375 qBraid credits; SV1 bills simulation time at 7.5 credits per minute. Batch thoughtfully, and print the job ID of every submission.
8. **Never submit to a QPU** (device IDs containing `:qpu:`) without the team's explicit go-ahead for that specific job. QPU jobs cost far more. Teams earn hardware credits by first running successfully on SV1, so get the SV1 result before proposing a hardware run, estimate its cost, and keep shots low.
9. **Transpile before submitting** to `["rz", "sx", "x", "cx"]`, as `prepare` does. Custom gates such as `XXPlusYYGate` or open-controlled gates may not survive export otherwise.
10. Watch the size. A 24-qubit statevector holds about 16.8 million amplitudes. Local optimization loops at that size are slow; prefer smaller encodings, fewer optimizer steps, or SV1 for the final evaluation.

### Credentials and safety

11. **Never put an API key in code, a notebook cell, an output, or a commit.** In qBraid Lab, `QbraidProvider()` picks up credentials automatically. Locally, use `qbraid configure` or the `QBRAID_API_KEY` environment variable.
12. Never print environment variables or credential files.

### Code and reproducibility

13. **Notebooks run top to bottom** in qBraid Lab with no edits, and are saved with outputs.
14. **Fix seeds** (`SEED = 7` in the starter) for simulators, optimizers and puzzle generation, and record them.
15. Support Qiskit 1.3 and later, including 2.x. Avoid APIs removed in 2.0 (V1 `Sampler` and `Estimator`, `execute`). Prefer `Statevector`, `AerSimulator`, `SparsePauliOp`, `transpile`.
16. Keep helper code readable. A judge asks team members to explain it, so favour clear functions over clever ones.

### Helping the team learn

17. Explain each step in plain words before writing the code for it. The goal of the event is understanding, and the Code and understanding criterion of the rubric tests every team member.
18. Keep a short log of what you generated and how it was checked. The team needs it for the AI use note in its repository's `README.md`.

## Useful directions

Point the team to these when they ask what to try. Each is a real research direction, not a guaranteed win.

- **Constrained mixers.** Extend the W-state start and XY mixer to the left/right qubits. Handle "a pair cannot serve both axes" with a penalty, or with a mixer over each cube's 6 valid choices.
- **Compact encodings.** Six choices fit in 3 qubits per cube (3N in total) instead of 6. The cost becomes higher order (more than two Z operators per term), so `cost_layer` needs multi-qubit Z rotations.
- **Hybrid splits.** Sample front/back 2-factors with a quantum circuit, then pair two that share no edge. Be explicit about which part is quantum.
- **Other algorithms.** VQE with a hardware-efficient ansatz, variational quantum imaginary time evolution, Grover adaptive search, or quantum annealing-style schedules.
- **Better optimization.** CVaR objectives, warm starts from the p = 1 grid, layer-by-layer growth, or angles transferred from small N to large N.

## Running headless

```bash
jupyter nbconvert --to notebook --execute --inplace starter_notebook.ipynb
```

The starter's SV1 cell runs locally while `submit_job` returns `None`. Once the team writes `submit_job`, a run without credentials raises `QbraidError`. The resource notebooks fall back to the local simulator without credentials and print a notice.
