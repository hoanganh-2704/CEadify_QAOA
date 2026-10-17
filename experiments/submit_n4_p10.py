"""Build the N=4, p=10 circuit from the saved round-6 angles and submit it to one qBraid device.

Usage (from the repo root, QBRAID_API_KEY set):
    .venv\\Scripts\\python.exe experiments\\submit_n4_p10.py <device_id> <shots>
    .venv\\Scripts\\python.exe experiments\\submit_n4_p10.py --build-only

Writes experiments/results/hardware_n4_p10.qasm (the exact circuit sent, after `prepare`) and
prints its SHA-256. Submitting returns immediately with the job id; collect the result later with
    experiments\\fetch_job.py <job_id> <label> 4
"""
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "experiments"), str(REPO)]

import solver  # noqa: E402

QASM = REPO / "experiments" / "results" / "hardware_n4_p10.qasm"
SEED, P = 1, 10


def build():
    record = json.loads((REPO / "experiments" / "results" / "round6.json").read_text())
    angles = next(r["angles"] for r in record["runs"] if r["seed"] == SEED and r["p"] == P)
    circuit = solver.hardware_circuit(solver.CUBES, angles, gauge="best")
    QASM.write_text(solver.qasm_text(circuit))
    digest = hashlib.sha256(QASM.read_bytes()).hexdigest()
    print(f"{QASM.name}: {circuit.num_qubits} qubits, {circuit.count_ops().get('cx', 0)} cx in file, sha256 {digest}")
    return solver.load_qasm(QASM)


def main(argv):
    circuit = build()
    if argv[0] == "--build-only":
        return
    from qbraid.runtime import QbraidProvider

    device_id, shots = argv[0], int(argv[1])
    device = QbraidProvider().get_device(device_id)
    print(f"{device_id}: {device.status().name}")
    job = device.run(circuit, shots=shots)
    print("qBraid job id:", job.id)


if __name__ == "__main__":
    main(sys.argv[1:])
