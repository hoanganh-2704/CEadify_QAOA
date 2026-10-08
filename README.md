# Instant Insanity on a Quantum Computer

The qBraid challenge at **Qiskit Fall Fest Connecticut 2026**, hosted by UConn Quantum Computing at the University of Connecticut, Storrs. Hacking runs on Saturday, October 17, 2026.

[<img src="https://qbraid-static.s3.amazonaws.com/logos/Launch_on_qBraid_white.png" width="150">](https://account.qbraid.com/launch?gitHubUrl=https://github.com/qBraid/fall-fest-ct-2026-challenge)

Event page: [account.qbraid.com/hackathons/2026/uconn-fallfest](https://account.qbraid.com/hackathons/2026/uconn-fallfest)

## The puzzle

You get four cubes. Each face is painted one of four colours. Stack the cubes into a tower so that every colour shows exactly once on each of the four sides: front, back, left and right.

There are 331,776 ways to stack the four cubes. Only 8 of them work, and those 8 are one tower seen from different angles. People have sold this puzzle as *Instant Insanity* since the 1960s, because it is so hard to solve by hand.

The puzzle is a **constraint problem**: many choices, a few rules, and very few choices that obey every rule. Scheduling, routing and chip layout problems have the same shape. Quantum optimization algorithms such as QAOA attack them by turning the rules into an energy and searching for the lowest energy state.

## The challenge

Solve the puzzle with a quantum algorithm, run it through qBraid, and explain what you learned.

| Level | Task |
|---|---|
| **Warm-up** | Work through `starter_notebook.ipynb`. It solves half the puzzle (the front and back of the tower) with QAOA on 12 qubits, and runs the circuit on the AWS SV1 simulator. |
| **Core** | Find a full solved tower for the four cubes in `starter_notebook.ipynb` with a quantum algorithm. Run it on SV1 through qBraid. Report how often your circuit returns a correct tower, what it costs in qubits, gates and credits, and how it compares with classical brute force and random guessing. |
| **Bonus** | Generalize to **N cubes and N colours**. Each cube's faces use N colours, and each colour must show exactly once on each of the four sides. Run your method for as many values of N as you can, and show how qubits, circuit depth and success rate grow with N. |

The general N-cube question is NP-complete (Robertson and Munro, 1978): no one knows a method that stays fast as N grows. N will be small on today's simulators. What we want to see is whether your idea **generalizes**, and how its cost grows.

Teams of all levels are welcome. A team that finishes the warm-up and one clear extension, with honest classical checks, can score well. See [GRADING.md](GRADING.md).

### What this challenge is for

- Getting started in **quantum optimization**: cost functions, Hamiltonians, QAOA and its relatives.
- Building intuition for **when and why** a quantum approach helps, and when it does not.
- Using the **qBraid platform**: qBraid Lab, the qBraid SDK and cloud simulators.
- Using **AI coding agents** for quantum work, with the checks that keep them honest. See [AGENTS.md](AGENTS.md).

## What is in this repository

```
README.md                 this file
GRADING.md                deliverables and the judging rubric
AGENTS.md                 instructions for AI coding agents working on a solution
starter_notebook.ipynb    the puzzle, the classical baseline, the cost Hamiltonian, and a QAOA warm-up on SV1
requirements.txt          Python packages for running locally
resources/
  01_qiskit_refresher.ipynb           circuits, measurement, parameters, Pauli operators, transpiling
  02_qbraid_sdk.ipynb                 qBraid providers, devices, jobs, the transpiler, cost discipline
  03_qaoa_maxcut_with_qbraid.ipynb    QAOA for a graph problem, end to end, submitted to SV1
```

New to quantum computing? Do the resources in order before the starter notebook. Each one takes about 35 to 40 minutes. Already know Qiskit? Start with the starter notebook. It takes about an hour.

## Getting started

### On qBraid (recommended)

1. Create a free account at [account.qbraid.com](https://account.qbraid.com) with the email you registered with.
2. Click **Launch on qBraid** above. qBraid Lab opens and clones this repository.
3. Open `starter_notebook.ipynb` and run the cells from the top. The first cell installs anything missing.

Inside qBraid Lab your credentials load automatically, so the SV1 cells submit real jobs with no setup. Follow your jobs on the [quantum jobs page](https://account.qbraid.com/quantum-jobs).

### On your own machine

```bash
git clone https://github.com/qBraid/fall-fest-ct-2026-challenge.git
cd fall-fest-ct-2026-challenge
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab
```

To submit to SV1 from your own machine, create an API key in your qBraid account, then run `qbraid configure` or set `QBRAID_API_KEY` in your shell. Never paste a key into a notebook cell. Without credentials, every SV1 cell runs on the local Aer simulator instead and says so.

### Compute and credits

- An SV1 job of the size in these notebooks costs **0.375 qBraid credits**. SV1 bills by simulation time at 7.5 credits per minute, so very deep or very wide circuits cost more.
- SV1 simulates up to 34 qubits. The full one-hot encoding of the four-cube puzzle needs 24 qubits, which SV1 handles easily. A laptop simulator slows down at that size, which is one reason to look for a smaller encoding.
- Debug on the local Aer simulator first. Send a circuit to SV1 once it works.
- Do not submit to quantum hardware (QPUs) unless the organizers say your team has credits for it. A QPU job costs far more than a simulator job.

<!-- TODO(organizers): how teams receive hackathon credits (organization invite or credit request). -->

## Submitting

Each team submits slides, working code, a short write-up and the IDs of its qBraid jobs. [GRADING.md](GRADING.md) lists every deliverable and the rubric.

## Credits

- The idea of solving Instant Insanity on a quantum computer comes from the IonQ challenge at SC Quantathon v2 (October 2025): [ionq-samples/SCQuantathon-v2](https://github.com/ionq-samples/SCQuantathon-v2). Thank you to IonQ for the original challenge. This repository contains new material written for Qiskit Fall Fest Connecticut 2026 and copies no code from that repository.
- The graph method in the starter notebook is the classic solution described in the [Wikipedia article on Instant Insanity](https://en.wikipedia.org/wiki/Instant_Insanity).
- E. Robertson and I. Munro, "NP-completeness, puzzles and games", *Utilitas Mathematica* 13 (1978) 99-116.

Challenge by [qBraid](https://www.qbraid.com) for Qiskit Fall Fest Connecticut 2026, hosted by UConn Quantum Computing, with IBM Quantum, QuantumCT and the UConn School of Computing.

## License

Apache-2.0. See [LICENSE](LICENSE).
