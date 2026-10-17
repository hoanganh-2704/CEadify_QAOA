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


# ---------------------------------------------------------------- round 3: full vs ring mixer only

MIXER_SEEDS = (0, 1, 2, 3, 4)
JITTER = 0.05
ROUND3_GAUGE = "best"


def mixer_runs(costs, solved, pairs):
    """Average-cost layer-by-layer training to p=7 for each jitter seed."""
    start = S.grid_p1(costs, solved, pairs=pairs)
    runs = []
    for seed in MIXER_SEEDS:
        t0 = time.perf_counter()
        angles, curve = S.train_layerwise(costs, solved, P_MAX, pairs, S.objective_average,
                                          jitter_seed=seed, jitter=JITTER, start=start)
        runs.append({"seed": seed, "p_solved": curve[-1][2], "avg_cost": curve[-1][1],
                     "train_s": time.perf_counter() - t0, "angles": angles.tolist()})
        print(f"    seed {seed}: P(solved) {curve[-1][2]:.4%}  <C> {curve[-1][1]:.4f}")
    return start, runs


def round3():
    costs, solved = problem()
    H = S.reduced_hamiltonian(S.CUBES, ROUND3_GAUGE)
    mixers = {}
    for name, pairs in S.MIXERS.items():
        print(f"mixer {name} ({len(pairs)} pairs per cube)")
        start, runs = mixer_runs(costs, solved, pairs)
        ps = [r["p_solved"] for r in runs]
        median_run = sorted(runs, key=lambda r: r["p_solved"])[len(runs) // 2]
        angles = np.array(median_run["angles"])
        circuit = S.tower_qaoa(S.CUBES, H, angles[:P_MAX], angles[P_MAX:], pairs)
        mixers[name] = {"pairs_per_cube": len(pairs), "grid_start": list(start), "runs": runs,
                        "median": float(np.median(ps)), "min": min(ps), "max": max(ps),
                        "circuit_angles_seed": median_run["seed"],
                        **grading_metrics(circuit)[1]}
        print(f"  {name}: median {np.median(ps):.4%}  min {min(ps):.4%}  max {max(ps):.4%}  "
              f"CX {mixers[name]['cx_grading']}  depth {mixers[name]['depth_grading']}")
    save("round3.json", {"objective": "average", "hamiltonian": f"reduced_{ROUND3_GAUGE}",
                         "jitter": JITTER, "p": P_MAX, "seeds": list(MIXER_SEEDS),
                         "transpile_call": 'transpile(qc, basis_gates=["rz","sx","x","cx"])',
                         "mixers": mixers})


# ---------------------------------------------------------------- round 4: objective only

ROUND4_OBJECTIVE = "gibbs1"


def round4():
    costs, solved = problem()
    pairs = S.MIXERS["full"]
    H = S.reduced_hamiltonian(S.CUBES, ROUND3_GAUGE)
    start = S.grid_p1(costs, solved, pairs=pairs)
    runs = []
    for seed in MIXER_SEEDS:
        t0 = time.perf_counter()
        angles, curve = S.train_layerwise(costs, solved, P_MAX, pairs,
                                          S.OBJECTIVES[ROUND4_OBJECTIVE],
                                          jitter_seed=seed, jitter=JITTER, start=start)
        runs.append({"seed": seed, "p_solved": curve[-1][2], "avg_cost": curve[-1][1],
                     "train_s": time.perf_counter() - t0, "angles": angles.tolist()})
        print(f"  seed {seed}: P(solved) {curve[-1][2]:.4%}  <C> {curve[-1][1]:.4f}")
    ps = [r["p_solved"] for r in runs]
    median_run = sorted(runs, key=lambda r: r["p_solved"])[len(runs) // 2]
    angles = np.array(median_run["angles"])
    circuit = S.tower_qaoa(S.CUBES, H, angles[:P_MAX], angles[P_MAX:], pairs)
    metrics = grading_metrics(circuit)[1]
    print(f"median {np.median(ps):.4%}  min {min(ps):.4%}  max {max(ps):.4%}  "
          f"CX {metrics['cx_grading']}  depth {metrics['depth_grading']}")
    round3_full = json.loads((RESULTS / "round3.json").read_text())["mixers"]["full"]
    save("round4.json", {
        "objective": ROUND4_OBJECTIVE, "eta": 1.0, "mixer": "full",
        "hamiltonian": f"reduced_{ROUND3_GAUGE}", "jitter": JITTER, "p": P_MAX,
        "seeds": list(MIXER_SEEDS), "grid_start": list(start), "runs": runs,
        "median": float(np.median(ps)), "min": min(ps), "max": max(ps),
        "circuit_angles_seed": median_run["seed"], **metrics,
        "transpile_call": 'transpile(qc, basis_gates=["rz","sx","x","cx"])',
        "comparison_round3_full_average": {k: round3_full[k] for k in ("median", "min", "max")},
    })


# ---------------------------------------------------------------- round 5: same recipe on N = 5

N5, PUZZLE_SEED5 = 5, 16
ROUND5_SEEDS = (0, 1, 2)


def brute_force_times(cubes):
    """Time the starter's two brute forces: 24^N orientations and the 6^N graph cases."""
    starter = S.load_starter()
    t0 = time.perf_counter()
    options = [starter["orientations"](cube) for cube in cubes]
    towers = sum(1 for tower in itertools.product(*options) if starter["solves"](tower))
    orient_s = time.perf_counter() - t0
    t0 = time.perf_counter()
    cases = starter["count_answers"](cubes)
    count_s = time.perf_counter() - t0
    print(f"brute force: {24 ** len(cubes):,} orientations -> {towers} towers in {orient_s:.1f}s; "
          f"count_answers -> {cases} of {6 ** len(cubes):,} cases in {count_s:.2f}s")
    return {"orientation_towers": towers, "orientation_s": orient_s,
            "count_answers": cases, "count_answers_s": count_s}


def round5():
    cubes = S.starter_puzzle(N5, PUZZLE_SEED5)
    costs, solved = S.cost_tensor(cubes), S.solved_mask(cubes)
    assert np.array_equal(solved, np.isclose(costs, 0)), "cost zeros != solved towers"
    brute = brute_force_times(cubes)
    pairs = S.MIXERS["full"]
    start = S.grid_p1(costs, solved, pairs=pairs)
    runs = []
    for seed in ROUND5_SEEDS:
        t0 = time.perf_counter()
        angles, curve = S.train_layerwise(costs, solved, P_MAX, pairs,
                                          S.OBJECTIVES[ROUND4_OBJECTIVE],
                                          jitter_seed=seed, jitter=JITTER, start=start)
        runs.append({"seed": seed, "p_solved": curve[-1][2], "avg_cost": curve[-1][1],
                     "train_s": time.perf_counter() - t0, "angles": angles.tolist()})
        print(f"  seed {seed}: exact subspace P(solved) {curve[-1][2]:.4%}  "
              f"<C> {curve[-1][1]:.4f}  {runs[-1]['train_s']:.0f}s")
    ps = [r["p_solved"] for r in runs]
    median_run = sorted(runs, key=lambda r: r["p_solved"])[len(runs) // 2]
    angles = np.array(median_run["angles"])
    H = S.reduced_hamiltonian(cubes, ROUND3_GAUGE)
    circuit = S.tower_qaoa(cubes, H, angles[:P_MAX], angles[P_MAX:], pairs)
    metrics = grading_metrics(circuit)[1]
    print(f"median {np.median(ps):.4%}  min {min(ps):.4%}  max {max(ps):.4%}  {metrics}  "
          f"{S.term_counts(H)}")
    save("round5.json", {
        "n": N5, "puzzle_seed": PUZZLE_SEED5, "cubes": cubes,
        "objective": ROUND4_OBJECTIVE, "eta": 1.0, "mixer": "full",
        "hamiltonian": f"reduced_{ROUND3_GAUGE}", **S.term_counts(H),
        "jitter": JITTER, "p": P_MAX, "seeds": list(ROUND5_SEEDS), "grid_start": list(start),
        "runs": runs, "median": float(np.median(ps)), "min": min(ps), "max": max(ps),
        "p_solved_kind": "exact, 6^5 legal-subspace simulation (no Aer at 30 qubits)",
        "circuit_angles_seed": median_run["seed"], **metrics,
        "transpile_call": 'transpile(qc, basis_gates=["rz","sx","x","cx"])',
        **S.random_baselines(solved), "brute_force": brute,
    })


# ---------------------------------------------------------------- round 6: depth sweep on N = 4

ROUND6_SEEDS = (0, 1, 2)
P_SWEEP = tuple(range(1, 11))


def round6():
    costs, solved = problem()
    pairs = S.MIXERS["full"]
    H = S.reduced_hamiltonian(S.CUBES, ROUND3_GAUGE)
    start = S.grid_p1(costs, solved, pairs=pairs)
    runs, train_s = [], {}
    for seed in ROUND6_SEEDS:
        t0 = time.perf_counter()
        layers = S.train_layers(costs, solved, max(P_SWEEP), pairs,
                                S.OBJECTIVES[ROUND4_OBJECTIVE],
                                jitter_seed=seed, jitter=JITTER, start=start)
        train_s[str(seed)] = time.perf_counter() - t0
        for p, angles, avg, hit in layers:
            runs.append({"seed": seed, "p": p, "p_solved": hit, "avg_cost": avg,
                         "angles": angles.tolist()})
        print(f"  seed {seed}: " + "  ".join(f"p{p}={hit:.2%}" for p, _, _, hit in layers)
              + f"  ({train_s[str(seed)]:.0f}s)")

    per_p, previous = {}, None
    for p in P_SWEEP:
        at_p = [r for r in runs if r["p"] == p]
        ps = [r["p_solved"] for r in at_p]
        median_run = sorted(at_p, key=lambda r: r["p_solved"])[len(at_p) // 2]
        angles = np.array(median_run["angles"])
        metrics = grading_metrics(S.tower_qaoa(S.CUBES, H, angles[:p], angles[p:], pairs))[1]
        block = {"median": float(np.median(ps)), "min": min(ps), "max": max(ps),
                 "circuit_angles_seed": median_run["seed"], **metrics}
        if previous is not None:
            block["added_cx"] = block["cx_grading"] - previous["cx_grading"]
            block["added_p_median_points"] = 100 * (block["median"] - previous["median"])
        per_p[str(p)] = previous = block
        print(f"p={p:2d}  median {block['median']:.2%}  [{block['min']:.2%}, {block['max']:.2%}]"
              f"  CX {block['cx_grading']}  depth {block['depth_grading']}")

    round4 = {r["seed"]: np.array(r["angles"])
              for r in json.loads((RESULTS / "round4.json").read_text())["runs"]}
    drift = {str(seed): float(np.max(np.abs(np.array(next(
        r["angles"] for r in runs if r["seed"] == seed and r["p"] == 7)) - round4[seed])))
        for seed in ROUND6_SEEDS}
    print("p=7 drift vs round4.json:", drift)
    save("round6.json", {
        "n": 4, "objective": ROUND4_OBJECTIVE, "eta": 1.0, "mixer": "full",
        "hamiltonian": f"reduced_{ROUND3_GAUGE}", "jitter": JITTER,
        "seeds": list(ROUND6_SEEDS), "p_values": list(P_SWEEP), "grid_start": list(start),
        "maxiter_rule": "80 at p=1, 220 for p<5, 400 for p>=5 (unchanged)",
        "train_s_per_seed_to_p10": train_s, "runs": runs, "per_p": per_p,
        "p7_drift_vs_round4": drift,
        "transpile_call": 'transpile(qc, basis_gates=["rz","sx","x","cx"])',
        **S.random_baselines(solved),
    })


# ---------------------------------------------------------------- round 7: local noise study (N = 3)

ROUND7_P = (1, 2, 3, 4)          # p = 6 dropped: one noisy 2000-shot run at p = 6 took 355 s
ROUND7_DROPPED = (6,)
ROUND7_SHOTS = 2000


def smallest_seed_with_answer(n, limit=100):
    count = S.load_starter()["count_answers"]
    for seed in range(limit):
        answers = count(S.starter_puzzle(n, seed))
        if answers:
            return seed, answers
    raise RuntimeError("no seed with an answer")


def round7():
    s, answers = smallest_seed_with_answer(3)
    cubes = S.starter_puzzle(3, s)
    costs, solved = S.cost_tensor(cubes), S.solved_mask(cubes)
    assert int(solved.sum()) == answers and np.array_equal(solved, np.isclose(costs, 0))
    pairs, model = S.MIXERS["full"], S.noise_model()
    H = S.reduced_hamiltonian(cubes, ROUND3_GAUGE)
    layers = S.train_layers(costs, solved, max(ROUND7_P), pairs, S.OBJECTIVES[ROUND4_OBJECTIVE],
                            jitter_seed=0, jitter=JITTER)
    rows = []
    for p, angles, _, exact in layers:
        if p not in ROUND7_P:
            continue
        compiled, metrics = grading_metrics(S.tower_qaoa(cubes, H, angles[:p], angles[p:], pairs))
        row = {"p": p, "angles": angles.tolist(), "exact_p": exact, **metrics,
               "exact_times_fidelity": exact * (1 - S.CX_ERROR) ** metrics["cx_grading"]}
        for kind, noise in (("noiseless", None), ("noisy", model)):
            t0 = time.perf_counter()
            counts = S.noisy_counts(compiled, noise, ROUND7_SHOTS, S.SEED)
            row[kind] = {**S.rates_from_counts(counts, cubes),
                         "run_s": time.perf_counter() - t0, "counts": counts}
        rows.append(row)
        print(f"p={p} exact {exact:.2%}  noiseless {row['noiseless']['p_solved']:.2%}  "
              f"noisy {row['noisy']['p_solved']:.2%}  one-hot {row['noisy']['one_hot_fraction']:.1%}"
              f"  post-sel {row['noisy']['p_post_selected']:.2%}  "
              f"P*0.99^CX {row['exact_times_fidelity']:.2%}  CX {metrics['cx_grading']}  "
              f"depth {metrics['depth_grading']}  noisy {row['noisy']['run_s']:.0f}s")
    base = S.random_baselines(solved)
    save("round7.json", {
        "n": 3, "puzzle_seed": s, "answers": answers, "cubes": cubes,
        "objective": ROUND4_OBJECTIVE, "mixer": "full", "hamiltonian": f"reduced_{ROUND3_GAUGE}",
        "jitter_seed": 0, "jitter": JITTER, "p_values": list(ROUND7_P),
        "dropped_p": list(ROUND7_DROPPED), "shots": ROUND7_SHOTS, "seed_simulator": S.SEED,
        "noise": {"cx_depolarizing": S.CX_ERROR, "sx_x_depolarizing": S.ONE_QUBIT_ERROR,
                  "rz": 0.0, "readout_flip": S.READOUT_ERROR, "routing": "none (no coupling map)"},
        "random_legal": base["random_legal"], "random_bits": base["random_bits"],
        "random_after_one_hot_postselection": base["random_legal"],
        "transpile_call": 'transpile(qc, basis_gates=["rz","sx","x","cx"])', "rows": rows,
    })


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "7"
    if which == "1":
        round1("--no-aer" not in sys.argv)
    else:
        {"2": round2, "3": round3, "4": round4, "5": round5, "6": round6, "7": round7}[which]()
