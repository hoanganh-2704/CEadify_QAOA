"""Submit only the selected rows to qBraid SV1 (never run by the agents; the team runs it on purpose).

The notebook-wide switch USE_QBRAID = True would send every small row (11 paid jobs). This script sends only the
jobs the review recommended, one at a time, and stops at the first failure:

    smoke   two-sided marker test circuit, 100 shots      (predicted 0.375 credits)
    C2      compact QAOA p = 24, 4,000 shots              (predicted 0.375 credits)
    G2      Grover K = 19, 4,000 shots                    (predicted 0.375 credits)
    W1      warm-up QAOA p = 2, 4,000 shots, optional     (predicted 0.375 credits)
    N5      Bonus N = 5 QAOA p = 24, 2,000 shots, optional (predicted 0.795 credits)

Run from the repository root, inside qBraid Lab or after `qbraid configure`:

    python scripts/run_sv1.py --jobs smoke C2 G2 --yes-spend-credits
    python scripts/run_sv1.py --jobs smoke C2 G2 W1 N5 --yes-spend-credits

Without --yes-spend-credits nothing is submitted: the script only builds the circuits and prints the predictions.
Predictions are our own offline guesses, not qBraid charges; SV1 bills by simulation time (7.5 credits per minute).
Each finished job is logged in results/jobs.json and its counts saved in results/sv1_counts/<tag>.json; the notebook
then replays those counts (REPLAY_SV1 = True, same circuit fingerprint, device and shot count) without paying again,
so re-executing solution.ipynb afterwards fills the SV1 rows and job ids of the results table.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from qiskit import QuantumCircuit  # noqa: E402

from src import runtime  # noqa: E402
from src.compact import angles_for, compact_qaoa, decode_tower, load_angles  # noqa: E402
from src.grover import grover_circuit  # noqa: E402
from src.puzzle import CUBES, instance  # noqa: E402
from src.report import success_rate  # noqa: E402
from src.warmup import constrained_qaoa, front_back_hamiltonian, good_strings, optimise_warmup, scan  # noqa: E402

JOBS = {"smoke": 100, "C2": 4000, "G2": 4000, "W1": 4000, "N5": 2000}


def build(tag):
    """The measurement-free circuit of one row, built exactly as the notebook builds it."""
    if tag == "smoke":
        qc = QuantumCircuit(3)        # the O1 reproducer: qubit 0 always 1, qubit 2 in superposition
        qc.x(0)
        qc.h(2)
        return qc, None
    if tag == "C2":
        return compact_qaoa(CUBES, *angles_for(load_angles("results/angles_Cc_N4.json"), 24)), CUBES
    if tag == "G2":
        return grover_circuit(CUBES, 19), CUBES
    if tag == "N5":
        cubes = instance(5)
        return compact_qaoa(cubes, *angles_for(load_angles("results/angles_Cc_N4.json"), 24)), cubes
    if tag == "W1":
        h_fb = front_back_hamiltonian(CUBES)
        gammas, betas = np.linspace(0, np.pi, 41), np.linspace(0, np.pi, 41)
        avg, _ = scan(h_fb, gammas, betas, good_strings(CUBES))
        i, j = np.unravel_index(avg.argmin(), avg.shape)
        best, _ = optimise_warmup(h_fb, [gammas[i], gammas[i], betas[j], betas[j]])
        return constrained_qaoa(h_fb, best[:2], best[2:]), None
    raise ValueError(tag)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", nargs="+", default=["smoke", "C2", "G2"], choices=sorted(JOBS))
    ap.add_argument("--yes-spend-credits", action="store_true", help="actually submit to SV1 (spends credits)")
    args = ap.parse_args()
    runtime.USE_QBRAID = args.yes_spend_credits
    if not args.yes_spend_credits:
        print("dry run: circuits are built and priced, nothing is submitted (add --yes-spend-credits to submit)")
    total = 0.0
    for tag in args.jobs:
        core, cubes = build(tag)
        qc = runtime.prepared(core)
        m = runtime.circuit_metrics(qc)
        predicted = runtime.predict_credits(qc)
        total += predicted
        print(f"{tag}: {m['qubits']} qubits, {m['cx']:,} CX, depth {m['depth']:,}, {JOBS[tag]:,} shots, "
              f"predicted {predicted} credits")
        if not args.yes_spend_credits:
            continue
        counts = runtime.run_on_qbraid(core, shots=JOBS[tag], tag=tag)
        if runtime.LAST_RUN["source"] not in ("sv1", "sv1-replay"):
            print(f"{tag} did not run on SV1 (see the messages above); stopping here")
            return 1
        if cubes is not None:
            s = success_rate(counts, lambda key: decode_tower(cubes, key))
            print(f"{tag}: P(correct tower) = {s['P']:.4f} +- {s['se']:.4f} on SV1, job {runtime.LAST_RUN['job_id']}")
        else:
            print(f"{tag}: {sum(counts.values()):,} shots back from SV1, job {runtime.LAST_RUN['job_id']}")
    print(f"predicted total for {args.jobs}: {total:.3f} credits (offline guess, not a qBraid charge)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
