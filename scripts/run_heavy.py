"""Compute the slow Bonus rows once (N = 6, 7, 8 compact QAOA at p = 24) and cache them in results/heavy_rows.json.

Run from the repository root:  python scripts/run_heavy.py            (about 15 minutes on an idle laptop)
Optional:                      python scripts/run_heavy.py --grover5  (adds Grover at N = 5, K = 48; several minutes)
The notebook reads the file and re-checks every exact P live, so a cached number can be checked on the spot.
"""
import argparse
import json
import platform
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import qiskit  # noqa: E402
import qiskit_aer  # noqa: E402

from src import runtime  # noqa: E402
from src.compact import Reduced, angles_for, compact_qaoa, decode_tower, load_angles  # noqa: E402
from src.puzzle import BONUS, SEED, baseline, instance  # noqa: E402
from src.report import compact_valid, make_row, success_rate, timestamp  # noqa: E402

OUT = ROOT / "results" / "heavy_rows.json"
SHOTS = 2000
P_LAYERS = 24


def qaoa_row(n, gammas, betas):
    """One Bonus row: compact QAOA with the N = 4 angles on make_puzzle(n, BONUS[n]), 2,000 Aer shots."""
    cubes = instance(n)
    t0 = time.perf_counter()
    circuit = compact_qaoa(cubes, gammas, betas)
    qc = runtime.prepared(circuit)
    t_transpile = time.perf_counter() - t0
    counts = runtime.run_on_qbraid(circuit, shots=SHOTS, tag=f"N{n}")
    success = success_rate(counts, lambda key: decode_tower(cubes, key), valid=compact_valid)
    p_exact = Reduced(cubes).P(gammas, betas)
    wall = time.perf_counter() - t0
    row = make_row(f"N{n}", "Bonus", f"N={n}, make_puzzle({n}, {BONUS[n]})", n, "compact 3 qubits/cube",
                   f"Cc QAOA p={P_LAYERS}, N=4 angles", qc, SHOTS, success,
                   baseline(n, "bits3N"), baseline(n, "valid6N"), p_exact=p_exact,
                   notes=f"cached by scripts/run_heavy.py; transpile {t_transpile:.0f} s, total {wall:.0f} s")
    print(f"N={n}: qubits {row['qubits']} cx {row['cx']} depth {row['depth']} P {row['P']:.4f} +- {row['P_se']:.4f} "
          f"(exact {p_exact:.4f}) n_invalid {row['n_invalid']} wall {wall:.0f} s", flush=True)
    return row, wall


def grover5_row():
    """Optional: Grover at N = 5 (K = 48) with the rules-only oracle; oracle synthesis takes minutes."""
    from src.grover import grover_circuit, grover_iterations, grover_success
    cubes = instance(5)
    k = grover_iterations(5)
    t0 = time.perf_counter()
    circuit = grover_circuit(cubes, k)
    qc = runtime.prepared(circuit)
    counts = runtime.run_on_qbraid(circuit, shots=SHOTS, tag="G5")
    success = success_rate(counts, lambda key: decode_tower(cubes, key), valid=compact_valid)
    wall = time.perf_counter() - t0
    row = make_row("G5", "Bonus", "N=5, make_puzzle(5, 16)", 5, "compact 3 qubits/cube", f"Grover K={k} (rule oracle)",
                   qc, SHOTS, success, baseline(5, "bits3N"), baseline(5, "valid6N"), p_exact=grover_success(5, k),
                   qubits_note="15 data + 1 ancilla + 1 marker",
                   notes=f"cached by scripts/run_heavy.py --grover5; P_exact is the sin^2 formula; total {wall:.0f} s")
    print(f"G5: qubits {row['qubits']} cx {row['cx']} depth {row['depth']} P {row['P']:.4f} wall {wall:.0f} s", flush=True)
    return row, wall


def write(rows, walls, command):
    """Write the rows and their provenance (command, seed, versions, time, wall seconds per row)."""
    OUT.parent.mkdir(parents=True, exist_ok=True)
    provenance = {"command": command, "seed": SEED, "shots": SHOTS, "qiskit": qiskit.__version__,
                  "qiskit_aer": qiskit_aer.__version__, "python": platform.python_version(),
                  "machine": platform.machine(), "timestamp": timestamp(), "wall_s": walls,
                  "angles": "results/angles_Cc_N4.json, p = 24", "device": runtime.AER_DEVICE}
    OUT.write_text(json.dumps({"provenance": provenance, "rows": rows}, indent=1))


def main():
    """Run the requested rows, writing the file after each one so a partial run still leaves results."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ns", type=int, nargs="*", default=[6, 7, 8], help="cube counts for the QAOA rows")
    parser.add_argument("--grover5", action="store_true", help="also run Grover at N = 5 (K = 48)")
    args = parser.parse_args()
    command = "python scripts/run_heavy.py " + " ".join(sys.argv[1:])
    gammas, betas = angles_for(load_angles(str(ROOT / "results" / "angles_Cc_N4.json")), P_LAYERS)
    rows, walls = [], {}
    for n in args.ns:
        row, wall = qaoa_row(n, gammas, betas)
        rows.append(row)
        walls[row["id"]] = round(wall, 1)
        write(rows, walls, command.strip())
    if args.grover5:
        row, wall = grover5_row()
        rows.append(row)
        walls[row["id"]] = round(wall, 1)
        write(rows, walls, command.strip())
    print("wrote", OUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
