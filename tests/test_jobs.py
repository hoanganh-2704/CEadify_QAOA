"""The real qBraid jobs: every finished job has its counts saved, and the SV1 / QPU rows of the results table are
exactly what the saved counts give through the project's decoders (no network, no new job)."""
import json
from pathlib import Path

import pytest

from src import runtime
from src.compact import angles_for, compact_qaoa, decode_tower, load_angles
from src.puzzle import CUBES, instance, is_two_factor
from src.report import results_table, success_rate
from src.warmup import decode_frontback

ROOT = Path(__file__).resolve().parents[1]
JOBS = json.loads((ROOT / "results" / "jobs.json").read_text())
ROWS = json.loads((ROOT / "results" / "results.json").read_text())
SV1_ROWS = [r for r in ROWS if r["id"].endswith("-SV1")]
QPU_ROWS = [r for r in ROWS if r["id"].endswith("-QPU")]


def _final(job_id):
    return [j for j in JOBS if j["job_id"] == job_id][-1]


def _counts_dir(device):
    return ROOT / "results" / ("qpu_counts" if ":qpu:" in device else "sv1_counts")


def _good_pick(key):
    picks = decode_frontback(key, 4)
    return picks if picks is not None and is_two_factor(CUBES, picks) else None


DECODERS = {"W1": _good_pick, "C2": lambda k: decode_tower(CUBES, k), "G2": lambda k: decode_tower(CUBES, k),
            "N5": lambda k: decode_tower(instance(5), k)}


def test_every_completed_job_has_a_counts_file():
    completed = {j["job_id"]: j for j in JOBS if j.get("status") == "COMPLETED"}
    assert completed, "no finished job in results/jobs.json"
    for job_id, job in completed.items():
        path = _counts_dir(job["device"]) / f"{job['tag']}.json"
        assert path.exists(), f"{job['tag']} ({job_id}) finished but {path} is missing"
        saved = json.loads(path.read_text())
        assert saved["job_id"] == job_id and saved["device"] == job["device"]
        assert sum(saved["counts"].values()) == job["shots"]


def test_every_counts_file_belongs_to_a_completed_job():
    for folder in ("sv1_counts", "qpu_counts"):
        for path in (ROOT / "results" / folder).glob("*.json"):
            saved = json.loads(path.read_text())
            assert _final(saved["job_id"])["status"] == "COMPLETED", path.name


def test_no_failed_job_has_a_table_row():
    failed = {j["job_id"] for j in JOBS if j.get("status") not in ("COMPLETED", "submitted")}
    assert not failed & {r["job_id"] for r in ROWS}


def test_sv1_rows_match_their_cached_counts():
    assert {r["id"] for r in SV1_ROWS} == {f"{t}-SV1" for t in ("W1", "C2", "G2", "N5")}
    for row in SV1_ROWS:
        tag = row["id"][:-4]
        saved = json.loads((ROOT / "results" / "sv1_counts" / f"{tag}.json").read_text())
        assert row["job_id"] == saved["job_id"] and row["device"] == runtime.SV1 == saved["device"]
        assert row["shots"] == saved["shots"] and row["cx"] == saved["cx"] and row["qubits"] == saved["qubits"]
        s = success_rate(runtime.strip_marker_safe(saved["counts"]), DECODERS[tag])
        assert s["n_good"] == row["n_good"] and s["P"] == pytest.approx(row["P"])
        assert row["credits"] == _final(saved["job_id"])["actual"]
        local = next(r for r in ROWS if r["id"] == tag)
        assert (local["cx"], local["depth"], local["P_exact"]) == (row["cx"], row["depth"], row["P_exact"])
        assert local["job_id"] == "" and local["device"].startswith("local AerSimulator")


@pytest.mark.parametrize("tag", ["C2", "N5"])
def test_sv1_cache_fingerprint_is_the_notebook_circuit(tag):
    cubes = CUBES if tag == "C2" else instance(5)
    core = compact_qaoa(cubes, *angles_for(load_angles(str(ROOT / "results" / "angles_Cc_N4.json")), 24))
    saved = json.loads((ROOT / "results" / "sv1_counts" / f"{tag}.json").read_text())
    assert runtime.replay_mismatch(saved, runtime.prepared(core), saved["shots"]) is None


def test_qpu_rows_match_their_counts():
    for row in QPU_ROWS:
        saved = next(json.loads(p.read_text()) for p in (ROOT / "results" / "qpu_counts").glob("*.json")
                     if json.loads(p.read_text())["job_id"] == row["job_id"])
        assert _final(row["job_id"])["status"] == "COMPLETED" and row["shots"] == saved["shots"]
        counts, _ = runtime.strip_marker_noisy(saved["counts"])
        n = 5 if row["N"] == 5 else 4
        decoder = _good_pick if row["id"].startswith("W1") else (lambda k: decode_tower(instance(n), k))
        assert success_rate(counts, decoder)["n_good"] == row["n_good"]


def test_replay_sv1_never_submits(monkeypatch, tmp_path):
    monkeypatch.setattr(runtime, "SV1_CACHE", str(tmp_path))
    monkeypatch.setattr(runtime, "submit_job", lambda *a, **k: pytest.fail("replay_sv1 must not submit"))
    monkeypatch.setattr(runtime, "aer_counts", lambda *a, **k: pytest.fail("replay_sv1 must not fall back"))
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(2)
    qc.h(0)
    assert runtime.replay_sv1(qc, 100, "nothing-saved") is None
    (tmp_path / "X.json").write_text(json.dumps({"tag": "X", "job_id": "j", "device": runtime.SV1, "shots": 100,
                                                 "fingerprint": "not-this-circuit", "counts": {"1000": 100}}))
    assert runtime.replay_sv1(qc, 100, "X") is None


def test_strip_marker_noisy_keeps_every_shot():
    raw = {"1010": 5, "0010": 3, "1011": 2}       # marker flips in 5 of 10 shots, Qiskit order by majority
    counts, stats = runtime.strip_marker_noisy(raw)
    assert counts == {"01": 10} and stats["qiskit_order"]
    assert stats["top_marker_error"] == 0.3 and stats["idle_qubit_error"] == 0.2
    counts, stats = runtime.strip_marker_noisy({"0011": 4, "0110": 1})   # reversed order by majority
    assert not stats["qiskit_order"] and counts == {"10": 4, "11": 1}
    assert stats["top_marker_error"] == 0.2 and stats["idle_qubit_error"] == 0.0


def test_job_cell_shows_cost():
    row = {k: "" for k in ("id", "puzzle", "encoding", "algorithm", "device", "qubits_note")}
    row.update(N=4, qubits=3, cx=0, depth=1, shots=10, P=0.5, P_se=0.1, P_exact=None, baseline_bits=0.1,
               baseline_subspace=0.2, job_id="job-1", credits=0.375)
    assert "job-1 (0.375 credits)" in results_table([row])
    row.update(job_id="", credits=None)
    assert "none (local run)" in results_table([row])
