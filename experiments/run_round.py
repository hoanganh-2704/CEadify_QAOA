"""Round runner. Local Statevector / Aer only; nothing is sent to qBraid.

Usage (repo root):
    .venv\\Scripts\\python.exe experiments/run_round.py 1 [--no-aer]   # round 1 baseline
    .venv\\Scripts\\python.exe experiments/run_round.py 2              # round 2
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
JITTER_SEEDS = (0, 1, 2, 3, 4)
OBJECTIVE_SEEDS = (0, 1, 2)
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


def verify_subspace(hamiltonian_fn=S.choice_hamiltonian, pairs=S.MIX_PAIRS, n_cubes=2, p=2,
                    seeds=(0, 1, 2, 3)):
    """Compare the 6^N simulator with Statevector of the real circuit."""
    cubes = S.CUBES[:n_cubes]
    H = hamiltonian_fn(cubes)
    costs = S.cost_tensor(cubes)
    worst_diff = worst_outside = 0.0
    for seed in seeds:
        rng = np.random.default_rng(seed)
        gammas, betas = rng.uniform(0, np.pi, p), rng.uniform(0, np.pi, p)
        probs = np.abs(Statevector(S.tower_qaoa(cubes, H, gammas, betas, pairs)).data) ** 2
        circuit_probs, outside = S.one_hot_probabilities(probs, n_cubes)
        sub_probs = np.abs(S.qaoa_state(costs, gammas, betas, pairs)) ** 2
        worst_diff = max(worst_diff, float(np.max(np.abs(circuit_probs - sub_probs))))
        worst_outside = max(worst_outside, abs(outside))
    print(f"subspace vs circuit [{hamiltonian_fn.__name__}, {len(pairs)} pairs], N={n_cubes}, "
          f"p={p}, {len(seeds)} angle sets: max |dP| = {worst_diff:.2e}, "
          f"outside one-hot = {worst_outside:.2e}")
    return {"max_abs_diff": worst_diff, "max_outside": worst_outside}


def circuit_row(H, angles, pairs=S.MIX_PAIRS):
    p = len(angles) // 2
    circuit = S.tower_qaoa(S.CUBES, H, angles[:p], angles[p:], pairs)
    compiled, grading = S.transpile_metrics(circuit, None)
    _, level1 = S.transpile_metrics(circuit, OPT_LEVEL)
    row = {"cx_grading": grading["cx"], "depth_grading": grading["depth"],
           "cx_opt1": level1["cx"], "depth_opt1": level1["depth"], "qubits": grading["qubits"]}
    return circuit, compiled, row


# ---------------------------------------------------------------- round 1

def round1(run_aer=True):
    check = verify_subspace()
    costs, solved = problem()
    base = S.random_baselines(solved)
    t0 = time.perf_counter()
    angles, curve = S.train_layerwise(costs, solved, P_MAX)
    train_s = time.perf_counter() - t0
    for p, avg, hit in curve:
        print(f"  p={p}  average cost {avg:.3f}  P(solved) {hit:.2%}")
    print("angles", np.round(angles, 4))
    H = S.choice_hamiltonian(S.CUBES)
    _, compiled, crow = circuit_row(H, angles)
    row = {"variant": f"baseline one-hot XY p={P_MAX}", "exact_p_solved": curve[-1][2],
           "avg_cost": curve[-1][1], **crow, **base, "train_s": train_s,
           "angles": angles.tolist()}
    if run_aer:
        row["aer"] = S.shot_metrics(S.aer_counts(compiled, SHOTS), S.CUBES)
    print(json.dumps({k: v for k, v in row.items() if k != "angles"}, indent=1, default=float))
    save("round1.json", {"verify": check, "rows": [row]})


# ---------------------------------------------------------------- round 2

def equivalence_rows(costs, solved, angles):
    """Same round-1 angles on the full and the reduced Hamiltonians."""
    exact = S.average_and_hit(S.qaoa_state(costs, angles[:P_MAX], angles[P_MAX:]),
                              costs, solved)[1]
    rows = []
    variants = [("full H (round 1)", S.choice_hamiltonian(S.CUBES), False),
                ("reduced H, reference 0", S.reduced_hamiltonian(S.CUBES), True),
                ("reduced H, best gauge", S.reduced_hamiltonian(S.CUBES, "best"), True)]
    for name, H, check_aer in variants:
        circuit, compiled, crow = circuit_row(H, angles)
        row = {"variant": name, **S.term_counts(H), **crow, "exact_subspace": exact}
        if check_aer:
            t0 = time.perf_counter()
            row["aer_statevector_p"], row["aer_outside"] = S.aer_exact_p_solved(compiled, solved)
            row["aer"] = S.shot_metrics(S.aer_counts(compiled, SHOTS), S.CUBES)
            row["aer_s"] = time.perf_counter() - t0
        print({k: v for k, v in row.items()})
        rows.append(row)
    return rows


def seeded_runs(costs, solved, pairs, objective, seeds, start):
    runs = []
    for seed in seeds:
        t0 = time.perf_counter()
        angles, curve = S.train_layerwise(costs, solved, P_MAX, pairs, objective,
                                          jitter_seed=seed, start=start)
        runs.append({"seed": seed, "p_solved": curve[-1][2], "avg_cost": curve[-1][1],
                     "train_s": time.perf_counter() - t0, "angles": angles.tolist()})
        print(f"    seed {seed}: P(solved) {curve[-1][2]:.2%}  <C> {curve[-1][1]:.3f}  "
              f"{runs[-1]['train_s']:.0f}s")
    return runs


def spread(runs):
    ps = sorted(r["p_solved"] for r in runs)
    return {"median": float(np.median(ps)), "min": ps[0], "max": ps[-1]}


def median_run(runs):
    return sorted(runs, key=lambda r: r["p_solved"])[len(runs) // 2]


def mixer_comparison(costs, solved, H):
    out = {}
    for name, pairs in S.MIXERS.items():
        print(f"  mixer {name} ({len(pairs)} pairs per cube)")
        start = S.grid_p1(costs, solved, pairs=pairs)
        runs = seeded_runs(costs, solved, pairs, S.objective_average, JITTER_SEEDS, start)
        rep = median_run(runs)
        _, compiled, crow = circuit_row(H, np.array(rep["angles"]), pairs)
        aer = S.shot_metrics(S.aer_counts(compiled, SHOTS), S.CUBES)
        out[name] = {"grid_start": start, "runs": runs, **spread(runs), **crow,
                     "median_seed": rep["seed"], "aer_median_run": aer}
        print(f"  {name}: {spread(runs)}  {crow}  Aer(median run) {aer}")
    return out


def objective_comparison(costs, solved, pairs, start, average_runs):
    out = {"average": [r for r in average_runs if r["seed"] in OBJECTIVE_SEEDS]}
    for name in ("cvar0.1", "gibbs1"):
        print(f"  objective {name}")
        out[name] = seeded_runs(costs, solved, pairs, S.OBJECTIVES[name], OBJECTIVE_SEEDS, start)
    return {name: {"runs": runs, **spread(runs)} for name, runs in out.items()}


def round2():
    checks = {f"{h.__name__}/{m}": verify_subspace(h, pairs)
              for h in (S.choice_hamiltonian, S.reduced_hamiltonian)
              for m, pairs in S.MIXERS.items()}
    costs, solved = problem()
    base = S.random_baselines(solved)
    t0 = time.perf_counter()
    angles, curve = S.train_layerwise(costs, solved, P_MAX)
    print(f"round-1 angles retrained in {time.perf_counter() - t0:.0f}s, "
          f"P(solved) {curve[-1][2]:.10f}")

    print("== Priority 1: equivalent rewrite, round-1 angles unchanged")
    equivalence = equivalence_rows(costs, solved, angles)

    print("== Priority 2: full vs ring mixer, reduced H (best gauge), "
          f"{len(JITTER_SEEDS)} seeds")
    H_best = S.reduced_hamiltonian(S.CUBES, "best")
    mixers = mixer_comparison(costs, solved, H_best)
    adopt_ring = mixers["ring"]["median"] >= mixers["full"]["median"] - 0.01
    winner = "ring" if adopt_ring else "full"
    print(f"adopt ring: {adopt_ring}")

    print(f"== Priority 3: objectives on the {winner} mixer, {len(OBJECTIVE_SEEDS)} seeds")
    objectives = objective_comparison(costs, solved, S.MIXERS[winner],
                                      mixers[winner]["grid_start"], mixers[winner]["runs"])
    for name, res in objectives.items():
        print(f"  {name}: median {res['median']:.2%}  min {res['min']:.2%}  max {res['max']:.2%}")

    save("round2.json", {"checks": checks, "baselines": base, "round1_angles": angles.tolist(),
                         "round1_p": curve[-1][2], "equivalence": equivalence,
                         "mixers": mixers, "adopt_ring": adopt_ring,
                         "objectives": objectives})


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "2"
    if which == "1":
        round1("--no-aer" not in sys.argv)
    else:
        round2()
