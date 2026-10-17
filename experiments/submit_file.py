"""Submit a saved, hash-checked QASM circuit to one qBraid device and return at once with the job id.

Usage (from the repo root, QBRAID_API_KEY set):
    .venv\\Scripts\\python.exe experiments\\submit_file.py <qasm path> <expected sha256> <device_id> <shots>

Collect the result later with experiments\\fetch_job.py <job_id> <label> [n_cubes].
"""
import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "experiments"), str(REPO)]

import solver  # noqa: E402
from qbraid.runtime import QbraidProvider  # noqa: E402


def rx_basis(circuit):
    """Rewrite sx as rx(pi/2) (equal up to a global phase). Braket's Rigetti route rejects the
    'v' gate that sx is translated to, but accepts rx/rz/cnot."""
    from qiskit import transpile

    return transpile(circuit, basis_gates=["rz", "rx", "cx", "x", "measure"], optimization_level=0)


def main(path, expected, device_id, shots, basis="sx"):
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if digest != expected:
        sys.exit(f"{path} sha256 {digest} does not match {expected}; not submitting")
    circuit = solver.load_qasm(path)
    if basis == "rx":
        circuit = rx_basis(circuit)
        print("gates sent:", dict(circuit.count_ops()))
    device = QbraidProvider().get_device(device_id)
    print(f"{device_id}: {device.status().name}")
    job = device.run(circuit, shots=int(shots))
    print("qBraid job id:", job.id)


if __name__ == "__main__":
    main(*sys.argv[1:6])
