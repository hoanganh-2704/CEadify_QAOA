"""Running circuits: two-sided marker, gate counts, local Aer, and the optional qBraid SV1 path.

Nothing here talks to qBraid unless USE_QBRAID is True and credentials exist. With the defaults
every circuit runs on the local Aer simulator and no qBraid module is imported.
"""
import hashlib
import io
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import qiskit_aer
from qiskit import QuantumCircuit, qpy, transpile
from qiskit_aer import AerSimulator

from resources.helpers import SEED

SV1 = "aws:aws:sim:sv1"
BASIS = ["rz", "sx", "x", "cx"]
USE_QBRAID = False          # flip to True only when the team decides to spend credits
REPLAY_SV1 = True           # reuse saved SV1 counts (results/sv1_counts/<tag>.json) instead of paying again
MAX_CREDITS_PER_JOB = 2.0   # our own offline prediction must stay below this (a pre-check, not a cap qBraid enforces)
MAX_QUOTE_CREDITS = 7.5     # qBraid quotes simulators as one full minute (7.5); a higher or missing quote is refused
MAX_QUBITS = 34             # SV1 limit
JOBS_LOG = "results/jobs.json"
SV1_CACHE = "results/sv1_counts"
AER_DEVICE = f"local AerSimulator (qiskit-aer {qiskit_aer.__version__}, seed {SEED})"
LAST_RUN = {"source": None, "device": None, "job_id": "", "credits": None}

ROOT = Path(__file__).resolve().parents[1]
_PREPARED = {}


def _path(p):
    """Resolve a results path against the repository root unless it is already absolute."""
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def _now():
    """Current UTC time as an ISO string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- two-sided marker

def prepare_safe(circuit, optimization_level=None):
    """Put the data on qubits 1..n between an idle |0> (q0) and an X marker (top), measure all, transpile."""
    if circuit.num_clbits or "measure" in circuit.count_ops():
        raise ValueError("prepare_safe expects a measurement-free circuit; it adds the measurements itself")
    n = circuit.num_qubits
    qc = QuantumCircuit(n + 2)
    qc.compose(circuit, range(1, n + 1), inplace=True)   # q0 stays idle, so the transpiler may use it as a clean ancilla
    qc.x(n + 1)
    qc.measure_all()
    return transpile(qc, basis_gates=BASIS, optimization_level=optimization_level, seed_transpiler=SEED)


def strip_marker_safe(raw):
    """Drop the two marker bits and return counts in Qiskit order, whichever end the provider put qubit 0."""
    keys = {k.replace(" ", ""): v for k, v in raw.items()}
    if all(k[0] == "1" and k[-1] == "0" for k in keys):
        return {k[1:-1]: v for k, v in keys.items()}
    if all(k[0] == "0" and k[-1] == "1" for k in keys):
        return {k[1:-1][::-1]: v for k, v in keys.items()}
    raise ValueError("marker pattern not found: expected keys '1...0' (Qiskit order) or '0...1' (reversed); "
                     "was the circuit built with prepare_safe?")


def fingerprint(circuit):
    """SHA-256 of the circuit's qpy serialisation (with a fixed name, so two equal circuits built separately match):
    changes whenever a gate, parameter value or qubit count changes."""
    buf = io.BytesIO()
    qpy.dump(circuit.copy(name="fingerprint"), buf)
    return hashlib.sha256(buf.getvalue()).hexdigest()


def prepared(circuit):
    """prepare_safe, remembered per circuit object and content, so metrics and counts come from the same transpiled
    circuit; a circuit mutated after the first call is prepared again."""
    fp = fingerprint(circuit)
    hit = _PREPARED.get(id(circuit))
    if hit is not None and hit[0] is circuit and hit[2] == fp:
        return hit[1]
    qc = prepare_safe(circuit)
    _PREPARED[id(circuit)] = (circuit, qc, fp)   # keep the circuit alive so its id is not reused
    return qc


# ---------------------------------------------------------------- metrics

def circuit_metrics(qc_prepared):
    """Qubits, CX count, depth, size and gate counts read straight from an already transpiled circuit."""
    ops = dict(qc_prepared.count_ops())
    return {"qubits": qc_prepared.num_qubits, "cx": ops.get("cx", 0), "depth": qc_prepared.depth(),
            "size": qc_prepared.size(), "ops": ops}


def trace_transpile(qc, **kw):
    """Transpile qc and return (circuit, rows), one row per pass that changed size, depth or 2-qubit count."""
    kw.setdefault("basis_gates", BASIS)
    kw.setdefault("seed_transpiler", SEED)
    rows = []

    def callback(pass_, dag, time, property_set, count):
        twoq = sum(1 for node in dag.op_nodes() if len(node.qargs) == 2)
        row = (count, type(pass_).__name__, dag.size(), dag.depth(), twoq, round(1e3 * time, 2))
        if not rows or row[2:5] != rows[-1][2:5]:
            rows.append(row)

    out = transpile(qc, callback=callback, **kw)
    return out, rows


def exact_distribution(qc_prepared):
    """Exact probabilities of the data keys of a prepared circuit (Statevector, markers stripped)."""
    from qiskit.quantum_info import Statevector
    bare = qc_prepared.remove_final_measurements(inplace=False)
    probs = Statevector(bare).probabilities_dict()
    return strip_marker_safe({k: p for k, p in probs.items() if p > 1e-14})


# ---------------------------------------------------------------- running

def aer_counts(qc_prepared, shots, seed=SEED):
    """Sample a prepared circuit on the local Aer simulator with a fixed seed."""
    return AerSimulator(seed_simulator=seed).run(qc_prepared, shots=shots).result().get_counts()


def qbraid_available():
    """True if qBraid credentials are configured: QBRAID_API_KEY or QBRAID_ACCESS_TOKEN in the environment (both are
    read by qbraid-core) or a ~/.qbraid/qbraidrc file; never reads or prints the values."""
    return (bool(os.environ.get("QBRAID_API_KEY")) or bool(os.environ.get("QBRAID_ACCESS_TOKEN"))
            or Path(os.path.expanduser("~/.qbraid/qbraidrc")).exists())


def predict_credits(qc):
    """Our own offline SV1 price guess: 7.5 credits per simulated minute, 3 s minimum (0.375)."""
    seconds = 2e-9 * qc.size() * 2 ** qc.num_qubits   # conservative fit to local Aer timings (gates x amplitudes)
    return round(max(0.375, 7.5 * seconds / 60), 3)


def estimate_credits(device_id=SV1, shots=1000, provider=None):
    """qBraid's read-only price quote for one job, or None when there is no quote (offline, no key, unpriced)."""
    if provider is None:
        if not (USE_QBRAID and qbraid_available()):
            return None
        from qbraid.runtime import QbraidProvider
        provider = QbraidProvider()
    try:
        quote = provider.client.estimate_cost(device_id, shots=shots)
    except Exception as err:   # network or service error: no quote, never fatal
        print(f"no price quote ({type(err).__name__})")
        return None
    if not quote.pricingAvailable or quote.estimatedCost is None:
        return None
    return float(quote.estimatedCost)


def check_submittable(qc):
    """Refuse anything that must not go to SV1: a QPU id, unbound parameters, too many qubits, no measurements."""
    if ":qpu:" in SV1:
        raise ValueError("QPU devices are refused by this function")
    if qc.parameters:
        raise ValueError("bind all parameters before submitting")
    if qc.num_qubits > MAX_QUBITS:
        raise ValueError(f"{qc.num_qubits} qubits > SV1 limit {MAX_QUBITS}")
    ops = qc.count_ops()
    if "measure" not in ops:
        raise ValueError("circuit has no measurements; use prepare_safe")
    extra = set(ops) - set(BASIS) - {"measure", "barrier"}
    if extra:
        raise ValueError(f"gates {sorted(extra)} are not in {BASIS}; use prepare_safe")


def submit_job(qc, shots, tag=None):
    """Run a prepared circuit on the SV1 simulator and return raw counts, or None to fall back to local Aer."""
    check_submittable(qc)
    if not USE_QBRAID:
        return None                                   # run_on_qbraid prints the Aer notice
    if not qbraid_available():
        print("No qBraid credentials found (qbraid configure or QBRAID_API_KEY); using local Aer.")
        return None
    from qbraid.exceptions import QbraidError
    from qbraid.runtime import QbraidProvider
    from qbraid_core.exceptions import QbraidException
    try:
        provider = QbraidProvider()                   # reads the credentials itself; nothing is printed
        device = provider.get_device(SV1)             # first network call
        print(device.id, "|", device.status().name, "|", device.num_qubits, "qubits")
        quote = estimate_credits(SV1, shots, provider=provider)
        predicted = predict_credits(qc)
        print(f"qBraid quote: {quote} credits (a quote, not a cap: the real charge is by simulation time); "
              f"our offline prediction: {predicted} credits")
        if predicted > MAX_CREDITS_PER_JOB:
            print(f"predicted cost {predicted} > budget {MAX_CREDITS_PER_JOB}; not submitted")
            return None
        if quote is None:
            print("no price quote available for this paid run; not submitted")
            return None
        if quote > MAX_QUOTE_CREDITS:
            print(f"quote {quote} > {MAX_QUOTE_CREDITS}; not submitted")
            return None
        job = device.run(qc, shots=shots, tags={"team": "kiarash", "seed": str(SEED), "tag": str(tag)})
        print("job id:", job.id)
        record = {"tag": tag, "job_id": job.id, "device": SV1, "shots": shots, "qubits": qc.num_qubits,
                  "cx": qc.count_ops().get("cx", 0), "depth": qc.depth(), "fingerprint": fingerprint(qc),
                  "estimated": quote, "predicted": predicted, "status": "submitted", "time": _now()}
        log_job(record)                               # logged before waiting, so the id survives a timeout
        result = job.result(timeout=1800)
        cost = result.details.get("cost")
        status = str(getattr(result.details.get("status"), "name", result.details.get("status")))
        log_job({**record, "actual": None if cost is None else float(cost), "status": status, "time": _now()})
        print("status:", status, "| cost (credits):", cost)
        if not result.success:
            print("job failed:", status)
            return None
        LAST_RUN.update(source="sv1", device=SV1, job_id=job.id, credits=None if cost is None else float(cost))
        return result.data.get_counts()
    except (QbraidError, QbraidException, OSError) as err:
        print(f"qBraid unavailable ({type(err).__name__}); using local Aer.")
        return None


def _cache_file(tag):
    """Where the saved SV1 counts for a tag live."""
    return _path(SV1_CACHE) / f"{tag}.json"


def replay_mismatch(saved, qc, shots):
    """Why a saved SV1 entry must not be replayed for this prepared circuit and shot count, or None if it may."""
    if not isinstance(saved, dict) or not saved.get("job_id") or not isinstance(saved.get("counts"), dict):
        return "incomplete entry (no job id or counts)"
    if "fingerprint" not in saved:
        return "legacy entry without a circuit fingerprint"
    if saved["fingerprint"] != fingerprint(qc):
        return "different circuit (fingerprint mismatch)"
    if saved.get("device") != SV1:
        return f"different device {saved.get('device')!r}"
    if saved.get("shots") != shots:
        return f"different shot count ({saved.get('shots')} saved, {shots} requested)"
    if sum(saved["counts"].values()) != shots:
        return f"counts total {sum(saved['counts'].values())} != {shots} shots"
    return None


def run_on_qbraid(circuit, shots=1000, tag=None):
    """Prepare the circuit, get counts (saved SV1 run, new SV1 job, or local Aer) and strip the markers."""
    qc = prepared(circuit)
    raw = None
    if REPLAY_SV1 and tag and _cache_file(tag).exists():
        saved = json.loads(_cache_file(tag).read_text())
        why = replay_mismatch(saved, qc, shots)
        if why:
            print(f"saved SV1 counts for {tag} not replayed: {why}")
        else:
            raw = saved["counts"]
            LAST_RUN.update(source="sv1-replay", device=saved["device"],
                            job_id=saved["job_id"], credits=saved.get("credits"))
            print(f"replaying SV1 counts for {tag}, job {LAST_RUN['job_id']} (no new job, no credits)")
    if raw is None:
        raw = submit_job(qc, shots, tag=tag)
        if raw is None:
            print("No qBraid job was sent, so this ran on the local Aer simulator.")
            raw = aer_counts(qc, shots)
            LAST_RUN.update(source="aer", device=AER_DEVICE, job_id="", credits=None)
        elif tag:
            cache = _cache_file(tag)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps({"tag": tag, "job_id": LAST_RUN["job_id"], "device": SV1, "shots": shots,
                                         "qubits": qc.num_qubits, "cx": qc.count_ops().get("cx", 0),
                                         "fingerprint": fingerprint(qc), "credits": LAST_RUN["credits"],
                                         "time": _now(), "counts": raw}, indent=1))
    return strip_marker_safe(raw)


def log_job(record):
    """Append one job record (ids, numbers, timestamps only) to the jobs log."""
    path = _path(JOBS_LOG)
    path.parent.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(path.read_text()) if path.exists() and path.read_text().strip() else []
    jobs.append(record)
    path.write_text(json.dumps(jobs, indent=1))
