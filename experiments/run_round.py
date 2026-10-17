"""Round runner. Local Statevector / Aer only; nothing is sent to qBraid.

Usage (repo root):
    .venv\\Scripts\\python.exe experiments/run_round.py 1 [--no-aer]   # round 1 baseline
    .venv\\Scripts\\python.exe experiments/run_round.py 2              # round 2: reduced H check only
"""
import itertools
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
TOL = 1e-9
DRIFT_TOL = 1e-6
GAUGES = ("reference0", "best")
RESULTS = HERE / "results"


def save(name, payload):
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / name).write_text(json.dumps(payload, indent=2, default=float))
    print(f"saved {RESULTS / name}")


def problem():
    costs = S.cost_tensor(S.CUBES)
    solved = S.solved_mask(S.CUBES)
    assert np.array_equal(solved, np.isclose(costs, 0)), "cost zeros != solved towers"
    return costs, solved


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
    print(f"subspace vs circuit, N={n_cubes}, p={p}: max |dP| = {worst_diff:.2e}, "
          f"outside one-hot = {worst_outside:.2e}")
    return {"max_abs_diff": worst_diff, "max_outside": worst_outside}


def grading_metrics(circuit):
    """CX and depth from the GRADING call transpile(qc, basis_gates=BASIS)."""
    compiled, m = S.transpile_metrics(circuit, None)
    return compiled, {"qubits": m["qubits"], "cx_grading": m["cx"], "depth_grading": m["depth"]}


# ---------------------------------------------------------------- round 1

def round1(run_aer=True):
    check = verify_subspace()
    costs, solved = problem()
    t0 = time.perf_counter()
    angles, curve = S.train_layerwise(costs, solved, P_MAX)
    train_s = time.perf_counter() - t0
    for p, avg, hit in curve:
        print(f"  p={p}  average cost {avg:.3f}  P(solved) {hit:.2%}")
    circuit = S.tower_qaoa(S.CUBES, S.choice_hamiltonian(S.CUBES), angles[:P_MAX], angles[P_MAX:])
    compiled, tm = S.transpile_metrics(circuit, OPT_LEVEL)
    row = {"variant": f"baseline one-hot XY p={P_MAX}", "exact_p_solved": curve[-1][2],
           "avg_cost": curve[-1][1], **tm, **S.random_baselines(solved), "train_s": train_s,
           "angles": angles.tolist()}
    if run_aer:
        row["aer"] = S.shot_metrics(S.aer_counts(compiled, SHOTS), S.CUBES)
    save("round1.json", {"verify": check, "rows": [row]})


# ---------------------------------------------------------------- round 2: reduced Hamiltonian only

def legal_energies(H, n_cubes):
    """Energy of H on every one-hot pick, as a (6,)*n tensor."""
    out = np.zeros((6,) * n_cubes)
    for index in itertools.product(range(6), repeat=n_cubes):
        bits = [0] * H.num_qubits
        for c, k in enumerate(index):
            bits[6 * c + k] = 1
        out[index] = S.energy(H, bits)
    return out


def fresh_training_drift(saved):
    """Retrain with the round-1 recipe only to record how far it lands from the saved
    vector. The result is not used anywhere else."""
    costs, solved = problem()
    fresh, _ = S.train_layerwise(costs, solved, P_MAX)
    drift = float(np.max(np.abs(fresh - saved)))
    print(f"fresh round-1 training drift from saved angles: {drift:.2e}"
          f"{' (above 1e-6, saved vector used)' if drift > DRIFT_TOL else ''}")
    return drift


def equivalence_check(gauge, angles, costs, solved, old_energies, psi_old):
    """Invariant for one gauge at the saved angles; returns the measurements."""
    H = S.reduced_hamiltonian(S.CUBES, gauge)
    new_energies = legal_energies(H, len(S.CUBES))
    energy_err = float(np.max(np.abs(new_energies - costs)))
    psi_new = S.qaoa_state(new_energies, angles[:P_MAX], angles[P_MAX:])
    overlap_n4 = float(abs(np.vdot(psi_old.ravel(), psi_new.ravel())))

    small = S.CUBES[:2]
    old_sv = Statevector(S.tower_qaoa(small, S.choice_hamiltonian(small),
                                      angles[:P_MAX], angles[P_MAX:]))
    new_sv = Statevector(S.tower_qaoa(small, S.reduced_hamiltonian(small, gauge),
                                      angles[:P_MAX], angles[P_MAX:]))
    overlap_n2 = float(abs(np.vdot(old_sv.data, new_sv.data)))

    passed = energy_err < TOL and abs(overlap_n4 - 1) < TOL and abs(overlap_n2 - 1) < TOL
    row = {"gauge": gauge, **S.term_counts(H), "energy_max_err_1296": energy_err,
           "overlap_n4_subspace": overlap_n4, "overlap_n2_circuit": overlap_n2,
           "p_solved_old": S.average_and_hit(psi_old, costs, solved)[1],
           "p_solved_new": S.average_and_hit(psi_new, costs, solved)[1], "passed": passed}
    if passed:  # gate counts are measurements, recorded only after the invariant holds
        circuit = S.tower_qaoa(S.CUBES, H, angles[:P_MAX], angles[P_MAX:])
        row.update(grading_metrics(circuit)[1])
    print(row)
    return row


def round2():
    round1_data = json.loads((RESULTS / "round1.json").read_text())
    round1_row = round1_data["rows"][0]
    angles = np.array(round1_row["angles"])
    costs, solved = problem()

    H_old = S.choice_hamiltonian(S.CUBES)
    old_energies = legal_energies(H_old, len(S.CUBES))
    psi_old = S.qaoa_state(old_energies, angles[:P_MAX], angles[P_MAX:])
    old_circuit = S.tower_qaoa(S.CUBES, H_old, angles[:P_MAX], angles[P_MAX:])
    baseline = {"hamiltonian": "full (round 1)", **S.term_counts(H_old),
                "p_solved": S.average_and_hit(psi_old, costs, solved)[1],
                **grading_metrics(old_circuit)[1],
                "aer_P_from_round1_json": round1_row.get("aer", {}).get("p_solved")}
    print(baseline)

    rows = [equivalence_check(g, angles, costs, solved, old_energies, psi_old) for g in GAUGES]
    save("round2.json", {
        "change": "reduced_hamiltonian (equivalent rewrite on the one-hot subspace)",
        "angles_used": angles.tolist(),
        "angles_source": "results/round1.json rows[0].angles (loaded, not retrained)",
        "fresh_training_drift_max_abs": fresh_training_drift(angles),
        "baseline_round1_circuit": baseline,
        "reduced": rows,
        "transpile_call": 'transpile(qc, basis_gates=["rz","sx","x","cx"])',
    })


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "2"
    if which == "1":
        round1("--no-aer" not in sys.argv)
    else:
        round2()
