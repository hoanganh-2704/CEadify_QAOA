"""Submit a few shallow circuits to a real QPU through qBraid (spends credits; the team runs it on purpose).

Deep circuits (thousands of CX) are pure noise on today's hardware, so only the shallowest rows go to the QPU:

    smoke   two-sided marker test circuit (3 data qubits), 100 shots
    W1p1    warm-up QAOA p = 1 (front/back pick only, 12 data qubits, about 166 CX), 500 shots
    G1      Grover K = 1 on the full 12-qubit compact register (about 225 CX), 500 shots
    Cc1     compact QAOA p = 1 on the full tower, p = 1 angles of results/angles_Cc_N4.json (about 368 CX), 500 shots
    G1N5    Bonus: Grover K = 1 on make_puzzle(5, 16), 15 data qubits (about 287 CX), 500 shots
    C2      the headline QAOA p = 24 row (8,648 CX; expected to be pure noise on hardware; run on request), 500 shots
    G2      Grover K = 19 on the full tower (3,987 CX; run on request), 500 shots
    N5      Bonus: compact QAOA p = 24 on make_puzzle(5, 16) with the N = 4 angles (14,266 CX; on request), 500 shots

Besides P(correct tower) each row records the fraction of shots that are still a legal code string (every cube in
0..5 for the compact register, one-hot per cube for the warm-up): it is 1 for the noiseless circuit and far below 1
for random bits, so it says how much of the circuit survived the noise even when the tower count is tiny.

Run from the repository root after `qbraid configure` (or with QBRAID_API_KEY set in the shell, never in a file):

    python scripts/run_qpu.py                                   # dry run: builds, measures, prints qBraid's quote
    python scripts/run_qpu.py --jobs smoke W1p1 G1 --yes-spend-qpu-credits
    python scripts/run_qpu.py --jobs W1p1 G1 G1N5 --shots G1=1000 --yes-spend-qpu-credits

Each job is logged in results/jobs.json and its raw counts saved in results/qpu_counts/<tag>.json, next to the
noiseless prediction for the same prepared circuit, so the README can compare QPU, SV1 and the exact value.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from qiskit import QuantumCircuit  # noqa: E402

from src import runtime  # noqa: E402
from src.compact import angles_for, compact_qaoa, decode_tower, load_angles  # noqa: E402
from src.grover import grover_circuit  # noqa: E402
from src.puzzle import CUBES, baseline, instance  # noqa: E402
from src.report import compact_valid, frontback_valid, success_rate  # noqa: E402
from src.warmup import constrained_qaoa, front_back_hamiltonian, good_strings, scan  # noqa: E402

DEVICE = "rigetti:rigetti:qpu:cepheus-1-108q"
JOBS = {"smoke": 100, "W1p1": 500, "G1": 500, "Cc1": 500, "G1N5": 500, "C2": 500, "G2": 500, "N5": 500}
COUNTS_DIR = ROOT / "results" / "qpu_counts"
ANGLES = ROOT / "results" / "angles_Cc_N4.json"


def build(tag):
    """The measurement-free circuit of one QPU row and a function that says whether a data key is a success."""
    if tag == "smoke":
        qc = QuantumCircuit(3)            # qubit 0 always 1, qubit 2 in superposition: tests the bit order
        qc.x(0)
        qc.h(2)
        return qc, lambda key: key[-1] == "1"
    if tag == "W1p1":
        h_fb = front_back_hamiltonian(CUBES)
        gammas, betas = np.linspace(0, np.pi, 41), np.linspace(0, np.pi, 41)
        good = set(good_strings(CUBES))
        avg, _ = scan(h_fb, gammas, betas, good)
        i, j = np.unravel_index(avg.argmin(), avg.shape)   # the starter's p = 1 grid optimum
        return constrained_qaoa(h_fb, [gammas[i]], [betas[j]]), lambda key: key in good
    if tag == "G1":
        return grover_circuit(CUBES, 1), lambda key: decode_tower(CUBES, key) is not None
    if tag == "Cc1":
        gammas, betas = angles_for(load_angles(ANGLES), 1)
        return compact_qaoa(CUBES, gammas, betas), lambda key: decode_tower(CUBES, key) is not None
    if tag == "G1N5":
        cubes = instance(5)
        return grover_circuit(cubes, 1), lambda key: decode_tower(cubes, key) is not None
    if tag == "C2":
        gammas, betas = angles_for(load_angles(ANGLES), 24)
        return compact_qaoa(CUBES, gammas, betas), lambda key: decode_tower(CUBES, key) is not None
    if tag == "G2":
        return grover_circuit(CUBES, 19), lambda key: decode_tower(CUBES, key) is not None
    if tag == "N5":
        cubes = instance(5)
        gammas, betas = angles_for(load_angles(ANGLES), 24)
        return compact_qaoa(cubes, gammas, betas), lambda key: decode_tower(cubes, key) is not None
    raise ValueError(tag)


def describe(tag):
    """Puzzle size n, the legal-key test and the two random-guess baselines (any bitstring, legal codes) of a tag."""
    if tag == "smoke":
        return 0, None, None, None
    if tag == "W1p1":
        return 4, frontback_valid, baseline(4, "fb_bits"), baseline(4, "fb_valid")
    n = 5 if tag.endswith("N5") else 4
    return n, compact_valid, baseline(n, "bits3N"), baseline(n, "valid6N")


def strip_marker_noisy(raw):
    """Hardware version of runtime.strip_marker_safe: readout errors flip some marker bits, so the bit order is
    decided by majority (which end reads mostly 1 and which mostly 0), every shot is kept, and the two marker
    error rates are returned so the row can say how well the plumbing qubits read out."""
    keys = {k.replace(" ", ""): v for k, v in raw.items()}
    total = sum(keys.values())
    first1 = sum(v for k, v in keys.items() if k[0] == "1") / total
    last1 = sum(v for k, v in keys.items() if k[-1] == "1") / total
    qiskit_order = first1 + (1 - last1) >= (1 - first1) + last1
    if qiskit_order:
        counts, top_err, idle_err = {}, 1 - first1, last1
    else:
        counts, top_err, idle_err = {}, 1 - last1, first1
    for k, v in keys.items():
        data = k[1:-1] if qiskit_order else k[1:-1][::-1]
        counts[data] = counts.get(data, 0) + v
    return counts, {"qiskit_order": qiskit_order, "top_marker_error": top_err, "idle_qubit_error": idle_err}


def parse_fetch(items):
    """--fetch TAG=JOBID: finished jobs to analyse again instead of submitting."""
    out = {}
    for item in items or []:
        tag, _, jid = item.partition("=")
        if tag not in JOBS or not jid:
            raise SystemExit(f"--fetch expects TAG=JOBID with a known tag, got {item!r}")
        out[tag] = jid
    return out


def seconds_until(hhmm):
    """Seconds from now to a local wall-clock time today (3600 when no deadline is given, at least 30)."""
    if not hhmm:
        return 3600
    from datetime import datetime
    h, m = (int(x) for x in hhmm.split(":"))
    now = datetime.now()
    return max(30, int((now.replace(hour=h, minute=m, second=0, microsecond=0) - now).total_seconds()))


def parse_shots(items):
    """--shots TAG=N overrides, as a dict."""
    out = {}
    for item in items or []:
        tag, _, n = item.partition("=")
        if tag not in JOBS or not n.isdigit():
            raise SystemExit(f"--shots expects TAG=N with a known tag, got {item!r}")
        out[tag] = int(n)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", nargs="+", default=["smoke", "W1p1", "G1"], choices=sorted(JOBS))
    ap.add_argument("--device", default=DEVICE)
    ap.add_argument("--shots", nargs="*", default=[], metavar="TAG=N", help="override the shots of a tag")
    ap.add_argument("--fetch", nargs="*", default=[], metavar="TAG=JOBID",
                    help="analyse a finished job of this tag again (no submission, no credits)")
    ap.add_argument("--max-credits", type=float, default=60.0, help="refuse a job whose qBraid quote is higher")
    ap.add_argument("--deadline", default=None, metavar="HH:MM",
                    help="local wall-clock time; a job not finished by then is logged as pending and skipped")
    ap.add_argument("--compiler-timeout", type=int, default=600,
                    help="seconds Rigetti's quilc may spend compiling (its default 180 s was not enough for G1)")
    ap.add_argument("--yes-spend-qpu-credits", action="store_true", help="actually submit (spends credits)")
    args = ap.parse_args()
    if ":qpu:" not in args.device:
        print("this script is for QPU devices; use scripts/run_sv1.py for SV1")
        return 1

    from qbraid.runtime import QbraidProvider
    provider = QbraidProvider()
    device = provider.get_device(args.device)
    print(device.id, "|", device.status().name, "|", device.num_qubits, "qubits")
    COUNTS_DIR.mkdir(parents=True, exist_ok=True)
    shots_of = {**JOBS, **parse_shots(args.shots)}
    fetch = parse_fetch(args.fetch)

    for tag in args.jobs:
        core, is_success = build(tag)
        n, is_valid, base_bits, base_valid = describe(tag)
        qc = runtime.prepare_safe(core)
        m = runtime.circuit_metrics(qc)
        ideal = runtime.exact_distribution(qc)
        p_ideal = sum(p for key, p in ideal.items() if is_success(key))
        valid_ideal = None if is_valid is None else sum(p for key, p in ideal.items() if is_valid(key))
        shots = shots_of[tag]
        quote = provider.client.estimate_cost(args.device, shots=shots)
        cost = float(quote.estimatedCost) if quote.pricingAvailable and quote.estimatedCost is not None else None
        print(f"{tag}: {m['qubits']} qubits, {m['cx']:,} CX, depth {m['depth']:,}, {shots} shots, "
              f"noiseless P {p_ideal:.4f} (legal-key fraction {valid_ideal}), random baseline {base_bits} any "
              f"bitstring / {base_valid} legal codes, qBraid quote {cost} credits")
        if tag in fetch:
            from qbraid.runtime.native import QbraidJob
            job = QbraidJob(fetch[tag], device=device)
            print(f"{tag}: fetching finished job {job.id} (no new submission)")
            result = job.result(timeout=600)
            status = str(getattr(result.details.get("status"), "name", result.details.get("status")))
            actual = result.details.get("cost")
        else:
            if not args.yes_spend_qpu_credits:
                continue
            if cost is None or cost > args.max_credits:
                print(f"{tag}: quote {cost} is missing or above {args.max_credits}; not submitted")
                return 1
            job = device.run(qc, shots=shots, tags={"team": "kiarash", "tag": tag},
                             runtime_options={"compiler_timeout": args.compiler_timeout})
            print(f"{tag}: job id {job.id}")
            record = {"tag": tag, "job_id": job.id, "device": args.device, "shots": shots, "qubits": m["qubits"],
                      "cx": m["cx"], "depth": m["depth"], "fingerprint": runtime.fingerprint(qc),
                      "estimated": cost, "compiler_timeout": args.compiler_timeout, "status": "submitted",
                      "time": runtime._now()}
            runtime.log_job(record)
            try:
                result = job.result(timeout=seconds_until(args.deadline))
            except Exception as err:   # timed out before the deadline: keep the id, the team can fetch it later
                print(f"{tag}: result pending at the deadline ({type(err).__name__}); job id {job.id}")
                runtime.log_job({**record, "status": "submitted, result pending", "time": runtime._now()})
                continue
            status = str(getattr(result.details.get("status"), "name", result.details.get("status")))
            actual = result.details.get("cost")
            runtime.log_job({**record, "status": status, "actual": None if actual is None else float(actual),
                             "time": runtime._now()})
        if not result.success:
            print(f"{tag}: job failed ({status})")
            if tag != args.jobs[-1]:
                continue
            return 1
        raw = result.data.get_counts()
        counts, marker = strip_marker_noisy(raw)
        print(f"{tag}: marker readout: Qiskit order {marker['qiskit_order']}, top marker error "
              f"{marker['top_marker_error']:.3f}, idle qubit error {marker['idle_qubit_error']:.3f}")
        s = success_rate(counts, lambda key: key if is_success(key) else None, valid=is_valid)
        n_total = sum(counts.values())
        valid_frac = None if s["n_invalid"] is None else 1 - s["n_invalid"] / n_total
        (COUNTS_DIR / f"{tag}.json").write_text(json.dumps(
            {"tag": tag, "job_id": job.id, "device": args.device, "shots": shots, "metrics": m, "N": n,
             "p_ideal": p_ideal, "p_qpu": s["P"], "se": s["se"], "n_good": s["n_good"], "n_total": n_total,
             "valid_fraction_ideal": valid_ideal, "valid_fraction_qpu": valid_frac, "marker": marker,
             "baseline_bits": base_bits, "baseline_valid": base_valid, "towers": s["objects"],
             "cost": None if actual is None else float(actual), "time": runtime._now(), "counts": raw}, indent=1, default=str))
        print(f"{tag}: QPU P = {s['P']:.4f} +- {s['se']:.4f} ({s['n_good']}/{n_total}) vs noiseless {p_ideal:.4f} "
              f"| legal-key fraction {valid_frac} vs noiseless {valid_ideal} | cost {actual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
