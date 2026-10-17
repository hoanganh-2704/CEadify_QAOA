"""Send the round-8 verified N=3, p=1 circuit to one qBraid device and record the result.

Usage (from the repo root):
    .venv\\Scripts\\python.exe experiments\\qbraid_job.py <device_id> <shots> <label>

Uses the notebook's own submit_job (loaded from solution.ipynb), checks the circuit file's
SHA-256 against round 8 before sending, keeps only shots whose marker reads 1, checks every
tower with solves(), and writes experiments/results/qbraid_<label>.json.
"""
import contextlib
import hashlib
import io
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "tests"), str(REPO / "experiments"), str(REPO)]

from notebook_loader import load_definitions  # noqa: E402
import solver  # noqa: E402

QASM = REPO / "experiments" / "results" / "hardware_n3_p1.qasm"
EXPECTED_SHA256 = "a666efe3ffc5203ba06ef75fd910b7e497f3722e2bd84b30e5d6cb9d64ce515e"
RANDOM_POST_SELECTED = 16 / 216


def main(device_id, shots, label):
    digest = hashlib.sha256(QASM.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        sys.exit(f"circuit file changed since round 8 (sha256 {digest}); not submitting")
    cubes = json.loads((REPO / "experiments" / "results" / "round7.json").read_text())["cubes"]
    circuit = solver.load_qasm(QASM)
    submit_job = load_definitions()["submit_job"]

    start = time.time()
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        raw = submit_job(circuit, shots, device_id)
    print(printed.getvalue(), end="")
    job_ids = [line.split(":", 1)[1].strip() for line in printed.getvalue().splitlines()
               if line.startswith("qBraid job id:")]
    row = solver.results_row(raw, cubes, marker=True, device=device_id, label=label)
    row.update(job_id=job_ids[0] if job_ids else None, shots_requested=shots,
               seconds=round(time.time() - start, 1), circuit_sha256=digest,
               qubits=circuit.num_qubits, random_post_selected=RANDOM_POST_SELECTED,
               raw_counts=raw)
    out = REPO / "experiments" / "results" / f"qbraid_{label}.json"
    out.write_text(json.dumps(row, indent=1))
    print(f"kept {row['kept']}/{row['total']} one-hot shots (marker dropped {row['marker_dropped']}); "
          f"solved {row['solved']}  ->  P(all) {row['p_all']:.2%}, "
          f"P(post-selected) {row['p_post_selected']:.2%} vs random {RANDOM_POST_SELECTED:.2%}")
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])
