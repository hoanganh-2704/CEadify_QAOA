"""Tests for src/runtime.py: two-sided marker, metrics, pass trace, and the credential-safe qBraid path."""
import json
import socket
import subprocess
import sys
import types

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter

from resources.helpers import prepare, strip_marker
from src import runtime
from src.runtime import (BASIS, SV1, aer_counts, circuit_metrics, exact_distribution, prepare_safe, prepared,
                         run_on_qbraid, strip_marker_safe, submit_job, trace_transpile)


def reproducer():
    """The O1 circuit x(0); h(2): qubit 0 is 1 in every shot, the case that fools the starter's strip_marker."""
    qc = QuantumCircuit(3)
    qc.x(0)
    qc.h(2)
    return qc


def reverse_keys(raw):
    """Counts as a provider that lists qubit 0 first would return them."""
    return {k[::-1]: v for k, v in raw.items()}


# ---------------------------------------------------------------- marker

def test_prepare_safe_layout():
    qc = prepare_safe(reproducer())
    assert qc.num_qubits == 5
    raw = aer_counts(qc, 200)
    assert all(k[0] == "1" and k[-1] == "0" for k in raw)
    assert set(qc.count_ops()) <= set(BASIS) | {"measure", "barrier"}


def test_prepare_safe_refuses_measured_circuit():
    qc = reproducer()
    qc.measure_all()
    with pytest.raises(ValueError):
        prepare_safe(qc)


def test_strip_marker_safe_both_orders():
    raw = aer_counts(prepare_safe(reproducer()), 2000)
    for counts in (strip_marker_safe(raw), strip_marker_safe(reverse_keys(raw))):
        assert set(counts) == {"001", "101"}
        assert abs(counts["001"] / 2000 - 0.5) < 0.05
    assert strip_marker_safe(raw) == strip_marker_safe(reverse_keys(raw))


def test_starter_strip_marker_trap():
    """Documents the trap: the starter decoder silently returns '011' on reversed keys."""
    raw = aer_counts(prepare(reproducer()), 500)
    assert set(strip_marker(raw)) == {"001", "101"}
    assert "011" in strip_marker(reverse_keys(raw))


def test_strip_marker_safe_bad_pattern():
    with pytest.raises(ValueError, match="marker"):
        strip_marker_safe({"1001": 5, "0000": 3})


def test_strip_marker_safe_spaces():
    assert strip_marker_safe({"1 01 0": 4}) == {"01": 4}


def test_prepared_is_memoised():
    core = reproducer()
    assert prepared(core) is prepared(core)


# ---------------------------------------------------------------- metrics

def test_circuit_metrics_warmup():
    from src.puzzle import CUBES
    from src.warmup import constrained_qaoa, front_back_hamiltonian
    core = constrained_qaoa(front_back_hamiltonian(CUBES), [0.4, 0.7], [0.3, 0.2], CUBES)
    assert prepare(core).num_qubits == 13
    m = circuit_metrics(prepare_safe(core))
    assert m["qubits"] == 14
    assert abs(m["cx"] - 300) <= 15
    assert m["cx"] == m["ops"]["cx"] and m["depth"] > 0 and m["size"] > m["cx"]


def test_trace_transpile_rows_match_output():
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.ccx(0, 1, 2)
    qc.rzz(0.3, 0, 2)
    out, rows = trace_transpile(qc, optimization_level=1)
    assert rows
    last = rows[-1]
    assert last[2] == out.size()
    assert last[4] == sum(1 for inst in out.data if inst.operation.num_qubits == 2)
    assert set(out.count_ops()) <= set(BASIS)


def test_exact_distribution_reproducer():
    probs = exact_distribution(prepare_safe(reproducer()))
    assert set(probs) == {"001", "101"}
    assert abs(probs["001"] - 0.5) < 1e-9


# ---------------------------------------------------------------- qBraid path, never online

def test_defaults_are_offline():
    assert runtime.USE_QBRAID is False
    assert ":qpu:" not in SV1


def test_submit_job_none_without_qbraid_import():
    """In a fresh interpreter, the default path returns None and never imports qbraid.runtime."""
    code = ("import sys; from qiskit import QuantumCircuit; from src.runtime import prepare_safe, submit_job;"
            "qc = QuantumCircuit(2); qc.h(0);"
            "assert submit_job(prepare_safe(qc), 10) is None;"
            "assert 'qbraid.runtime' not in sys.modules; assert 'qbraid' not in sys.modules; print('ok')")
    out = subprocess.run([sys.executable, "-c", code], cwd=runtime.ROOT, capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "ok"


def _no_network(monkeypatch):
    """Make any socket creation fail loudly."""
    def boom(*a, **k):
        raise AssertionError("network access attempted")
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)


def test_use_qbraid_without_credentials_is_none(monkeypatch, capsys):
    _no_network(monkeypatch)
    monkeypatch.setattr(runtime, "USE_QBRAID", True)
    assert runtime.qbraid_available() is False
    assert submit_job(prepare_safe(reproducer()), 10) is None
    assert "credentials" in capsys.readouterr().out


@pytest.mark.parametrize("case", ["qpu", "params", "qubits", "nomeasure", "basis"])
def test_submit_job_refusals(monkeypatch, case):
    monkeypatch.setattr(runtime, "USE_QBRAID", True)
    qc = prepare_safe(reproducer())
    if case == "qpu":
        monkeypatch.setattr(runtime, "SV1", "aws:ionq:qpu:forte-1")
    elif case == "params":
        qc = QuantumCircuit(1)
        qc.rz(Parameter("t"), 0)
        qc.measure_all()
    elif case == "qubits":
        qc = QuantumCircuit(35)
        qc.measure_all()
    elif case == "nomeasure":
        qc = QuantumCircuit(2)
        qc.x(0)
    elif case == "basis":
        qc = QuantumCircuit(2)
        qc.h(0)
        qc.measure_all()
    with pytest.raises(ValueError):
        submit_job(qc, 10)


def _fake_entry(core, shots=100, **over):
    qc = prepared(core)
    entry = {"tag": "X0", "job_id": "fake-job-123", "device": SV1, "shots": shots, "qubits": qc.num_qubits,
             "cx": qc.count_ops().get("cx", 0), "fingerprint": runtime.fingerprint(qc),
             "counts": {"10010": int(0.6 * shots), "11010": shots - int(0.6 * shots)}}
    entry.update(over)
    return entry


def test_run_on_qbraid_replays_cached_counts(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(runtime, "SV1_CACHE", str(tmp_path / "sv1_counts"))
    (tmp_path / "sv1_counts").mkdir()
    core = reproducer()
    (tmp_path / "sv1_counts" / "X0.json").write_text(json.dumps(_fake_entry(core)))
    counts = run_on_qbraid(core, shots=100, tag="X0")
    assert counts == {"001": 60, "101": 40}
    assert runtime.LAST_RUN["device"] == SV1 and runtime.LAST_RUN["job_id"] == "fake-job-123"
    assert "replaying" in capsys.readouterr().out


@pytest.mark.parametrize("case", ["legacy", "other_circuit", "other_shots", "bad_total", "other_device", "no_job"])
def test_replay_rejects_mismatched_cache(monkeypatch, tmp_path, capsys, case):
    """F2 regression: saved counts are replayed only for the same circuit content, device and shot count."""
    monkeypatch.setattr(runtime, "SV1_CACHE", str(tmp_path / "sv1_counts"))
    (tmp_path / "sv1_counts").mkdir()
    core = reproducer()
    entry = _fake_entry(core)
    if case == "legacy":
        del entry["fingerprint"]                     # written before the fingerprint existed
    elif case == "other_circuit":
        other = QuantumCircuit(3)                    # same width, same CX count (zero), different gates
        other.x(0)
        other.x(2)
        entry = _fake_entry(other)
    elif case == "other_shots":
        entry["shots"] = 1000
    elif case == "bad_total":
        entry["counts"] = {"10010": 30}
    elif case == "other_device":
        entry["device"] = "aws:ionq:qpu:forte-1"
    elif case == "no_job":
        entry["job_id"] = ""
    (tmp_path / "sv1_counts" / "X0.json").write_text(json.dumps(entry))
    counts = run_on_qbraid(core, shots=100, tag="X0")
    out = capsys.readouterr().out
    assert "not replayed" in out and "local Aer" in out
    assert runtime.LAST_RUN["source"] == "aer" and sum(counts.values()) == 100 and set(counts) == {"001", "101"}


def test_fingerprint_depends_on_content_only():
    a, b = prepare_safe(reproducer()), prepare_safe(reproducer())
    assert a.name != b.name and runtime.fingerprint(a) == runtime.fingerprint(b)
    other = reproducer()
    other.x(2)
    assert runtime.fingerprint(prepare_safe(other)) != runtime.fingerprint(a)


def test_prepared_follows_mutation():
    """F9 regression: a circuit changed after the first call is prepared again."""
    core = QuantumCircuit(1)
    before = prepared(core)
    assert exact_distribution(before) == {"0": 1.0}
    core.x(0)
    after = prepared(core)
    assert after is not before and exact_distribution(after) == {"1": 1.0}
    assert prepared(core) is after


def test_qbraid_available_access_token(monkeypatch):
    """F6: an access token alone (what qbraid-core reads as QBRAID_ACCESS_TOKEN) counts as credentials."""
    monkeypatch.delenv("QBRAID_API_KEY", raising=False)
    monkeypatch.setenv("QBRAID_ACCESS_TOKEN", "FAKE-TOKEN")
    monkeypatch.setattr(runtime.Path, "exists", lambda self: False)
    assert runtime.qbraid_available() is True
    monkeypatch.delenv("QBRAID_ACCESS_TOKEN")
    assert runtime.qbraid_available() is False


def test_run_on_qbraid_falls_back_to_aer(capsys):
    counts = run_on_qbraid(reproducer(), shots=200, tag=None)
    assert set(counts) == {"001", "101"} and sum(counts.values()) == 200
    assert runtime.LAST_RUN["source"] == "aer" and runtime.LAST_RUN["job_id"] == ""
    assert "local Aer" in capsys.readouterr().out


def test_fake_key_never_printed(monkeypatch, capsys):
    """With a key in the environment and qBraid switched on, the key value never reaches stdout."""
    monkeypatch.setenv("QBRAID_API_KEY", "FAKE-KEY")
    _no_network(monkeypatch)
    run_on_qbraid(reproducer(), shots=50, tag=None)          # USE_QBRAID False: Aer
    monkeypatch.setattr(runtime, "USE_QBRAID", True)
    try:
        run_on_qbraid(reproducer(), shots=50, tag=None)      # tries qBraid, network refused
    except AssertionError:
        pass
    out = capsys.readouterr()
    assert "FAKE-KEY" not in out.out and "FAKE-KEY" not in out.err


# ---------------------------------------------------------------- full SV1 path against a mocked qBraid

class _Quote:
    pricingAvailable = True
    estimatedCost = 7.5


class _Job:
    id = "aws:aws:sim:sv1-fake-job"

    def __init__(self, qc, shots):
        self.counts = aer_counts(qc, shots)

    def result(self, timeout=None):
        data = types.SimpleNamespace(get_counts=lambda: self.counts)
        return types.SimpleNamespace(success=True, data=data, details={"cost": "0.375", "status": "COMPLETED"})


class _Device:
    id = SV1
    num_qubits = 34
    submitted = []

    def status(self):
        return types.SimpleNamespace(name="ONLINE")

    def run(self, qc, shots, tags=None):
        self.submitted.append((qc.num_qubits, shots, tags))
        return _Job(qc, shots)


class _Provider:
    def __init__(self, *a, **k):
        self.client = types.SimpleNamespace(estimate_cost=lambda device, shots=None: _Quote())

    def get_device(self, device_id):
        assert device_id == SV1
        return _Device()


def test_sv1_path_with_mock_provider(monkeypatch, tmp_path, capsys):
    """Quote, budget guard, job-id logging, cache writing and two-sided decoding, with qBraid mocked out."""
    import qbraid.runtime
    monkeypatch.setattr(qbraid.runtime, "QbraidProvider", _Provider)
    monkeypatch.setattr(runtime, "USE_QBRAID", True)
    monkeypatch.setattr(runtime, "JOBS_LOG", str(tmp_path / "jobs.json"))
    monkeypatch.setattr(runtime, "SV1_CACHE", str(tmp_path / "sv1_counts"))
    monkeypatch.setenv("QBRAID_API_KEY", "FAKE-KEY")
    _no_network(monkeypatch)
    counts = run_on_qbraid(reproducer(), shots=100, tag="X0")
    assert set(counts) == {"001", "101"} and sum(counts.values()) == 100
    assert runtime.LAST_RUN["device"] == SV1 and runtime.LAST_RUN["credits"] == 0.375
    jobs = json.loads((tmp_path / "jobs.json").read_text())
    assert [j["status"] for j in jobs] == ["submitted", "COMPLETED"]
    assert jobs[-1]["job_id"] == _Job.id and jobs[-1]["actual"] == 0.375 and jobs[-1]["estimated"] == 7.5
    assert json.loads((tmp_path / "sv1_counts" / "X0.json").read_text())["job_id"] == _Job.id
    out = capsys.readouterr().out
    assert "job id:" in out and "FAKE-KEY" not in out
    # second call replays the cache: no new submission
    n_before = len(_Device.submitted)
    assert run_on_qbraid(reproducer(), shots=100, tag="X0") == counts
    assert len(_Device.submitted) == n_before


def test_budget_guard_refuses_big_job(monkeypatch, capsys):
    import qbraid.runtime
    monkeypatch.setattr(qbraid.runtime, "QbraidProvider", _Provider)
    monkeypatch.setattr(runtime, "USE_QBRAID", True)
    monkeypatch.setattr(runtime, "MAX_CREDITS_PER_JOB", 0.1)
    monkeypatch.setenv("QBRAID_API_KEY", "FAKE-KEY")
    n_before = len(_Device.submitted)
    assert submit_job(prepare_safe(reproducer()), 10) is None
    assert len(_Device.submitted) == n_before
    assert "not submitted" in capsys.readouterr().out


def test_missing_quote_refuses_submission(monkeypatch, capsys):
    """F7: a paid run with no price quote is not submitted."""
    import qbraid.runtime

    class NoQuote(_Provider):
        def __init__(self, *a, **k):
            self.client = types.SimpleNamespace(estimate_cost=lambda device, shots=None: types.SimpleNamespace(
                pricingAvailable=False, estimatedCost=None))

    monkeypatch.setattr(qbraid.runtime, "QbraidProvider", NoQuote)
    monkeypatch.setattr(runtime, "USE_QBRAID", True)
    monkeypatch.setenv("QBRAID_API_KEY", "FAKE-KEY")
    n_before = len(_Device.submitted)
    assert submit_job(prepare_safe(reproducer()), 10) is None
    assert len(_Device.submitted) == n_before
    out = capsys.readouterr().out
    assert "no price quote" in out and "not submitted" in out and "FAKE-KEY" not in out


def test_provider_error_falls_back(monkeypatch, capsys):
    import qbraid.runtime
    from qbraid.exceptions import QbraidError

    class Broken(_Provider):
        def get_device(self, device_id):
            raise QbraidError("no auth")

    monkeypatch.setattr(qbraid.runtime, "QbraidProvider", Broken)
    monkeypatch.setattr(runtime, "USE_QBRAID", True)
    monkeypatch.setenv("QBRAID_API_KEY", "FAKE-KEY")
    assert submit_job(prepare_safe(reproducer()), 10) is None
    assert "using local Aer" in capsys.readouterr().out
