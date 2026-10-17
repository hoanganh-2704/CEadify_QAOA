"""Round runner: verify the subspace simulator, then reproduce the N=4 baseline.

Usage (repo root):  .venv\\Scripts\\python.exe experiments/run_round.py [--no-aer]
Local Statevector / Aer only. Nothing is sent to qBraid.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
from qiskit.quantum_info import Statevector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

OPT_LEVEL = 1
SHOTS = 1000
P_MAX = 7


def verify_subspace(n_cubes=2, p=2, seeds=(0, 1, 2, 3)):
    """Compare the 6^N simulator with Statevector of the real circuit."""
    cubes = S.CUBES[:n_cubes]
    H = S.choice_hamiltonian(cubes)
    costs = S.cost_tensor(cubes)
    worst_diff = worst_outside = 0.0
    for seed in seeds:
        rng = np.random.default_rng(seed)
        gammas, betas = rng.uniform(0, np.pi, p), rng.uniform(0, np.pi, p)
        probs = np.abs(Statevector(S.tower_qaoa(cubes, H, gammas, betas)).data) ** 2
        circuit_probs, outside = S.one_hot_probabilities(probs, n_cubes)
        sub_probs = np.abs(S.qaoa_state(costs, gammas, betas)) ** 2
        worst_diff = max(worst_diff, float(np.max(np.abs(circuit_probs - sub_probs))))
        worst_outside = max(worst_outside, abs(outside))
    print(f"subspace vs circuit, N={n_cubes}, p={p}, {len(seeds)} random angle sets: "
          f"max |dP| = {worst_diff:.2e}, max mass outside one-hot = {worst_outside:.2e}")
    return {"max_abs_diff": worst_diff, "max_outside": worst_outside}


def baseline(run_aer=True):
    costs = S.cost_tensor(S.CUBES)
    solved = S.solved_mask(S.CUBES)
    assert np.array_equal(solved, np.isclose(costs, 0)), "cost zeros != solved towers"
    base = S.random_baselines(solved)

    t0 = time.perf_counter()
    angles, curve = S.train_layerwise(costs, solved, P_MAX)
    train_s = time.perf_counter() - t0
    for p, avg, hit in curve:
        print(f"  p={p}  average cost {avg:.3f}  P(solved) {hit:.2%}")
    print("angles", np.round(angles, 4))

    H = S.choice_hamiltonian(S.CUBES)
    circuit = S.tower_qaoa(S.CUBES, H, angles[:P_MAX], angles[P_MAX:])
    compiled, tm = S.transpile_metrics(circuit, OPT_LEVEL)

    row = {"variant": f"baseline one-hot XY p={P_MAX}", "exact_p_solved": curve[-1][2],
           "avg_cost": curve[-1][1], **tm, **base, "train_s": train_s,
           "angles": angles.tolist()}
    if run_aer:
        t0 = time.perf_counter()
        shots = S.shot_metrics(S.aer_counts(compiled, SHOTS), S.CUBES)
        row.update(aer=shots, aer_s=time.perf_counter() - t0)
    return row


def print_table(rows):
    header = (f"{'variant':<28}{'exact P':>9}{'Aer P':>9}{'valid':>7}{'qubits':>7}"
              f"{'depth':>7}{'CX':>7}{'opt':>5}{'rand legal':>12}{'rand bits':>11}")
    print(header)
    print("-" * len(header))
    for r in rows:
        aer = r.get("aer")
        aer_p = f"{aer['p_solved']:.2%}" if aer else "-"
        valid = f"{aer['valid'] / aer['shots']:.0%}" if aer else "-"
        print(f"{r['variant']:<28}{r['exact_p_solved']:>9.2%}{aer_p:>9}{valid:>7}"
              f"{r['qubits']:>7}{r['depth']:>7}{r['cx']:>7}{r['optimization_level']:>5}"
              f"{r['random_legal']:>12.3%}{r['random_bits']:>11.2e}")


def main():
    run_aer = "--no-aer" not in sys.argv
    check = verify_subspace()
    row = baseline(run_aer)
    print()
    print_table([row])
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    (out / "round1.json").write_text(json.dumps({"verify": check, "rows": [row]}, indent=2))
    print(f"saved {out / 'round1.json'}")


if __name__ == "__main__":
    main()
