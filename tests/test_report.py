"""Tests for src/report.py: verified-only success rates, the GRADING table and results.json round trip."""
import json
import math

from qiskit import QuantumCircuit

from src import report, runtime
from src.puzzle import CUBES, tower_from, verify_choice
from src.report import GRADING_HEADER, ROW_KEYS, make_row, results_table, success_rate, wald

KNOWN = "011001100101"   # compact key of a solved tower on CUBES (codes [5, 4, 1, 3])


def compact_decoder(key):
    """Small stand-in for compact.decode_tower so this test does not depend on agent A's module."""
    from src.puzzle import CHOICES
    key = key.replace(" ", "")[-12:]
    bits = key[::-1]
    codes = [int(bits[3 * c]) + 2 * int(bits[3 * c + 1]) + 4 * int(bits[3 * c + 2]) for c in range(4)]
    if any(k >= 6 for k in codes):
        return None
    choice = [CHOICES[k] for k in codes]
    return tower_from(CUBES, choice) if verify_choice(CUBES, choice) else None


def test_known_key_is_a_tower():
    assert compact_decoder(KNOWN) is not None


def test_success_rate_counts_only_verified():
    counts = {KNOWN: 30, "111111111111": 50, "000000000000": 15, "0110 0110 0101": 5}
    valid = lambda k: all(c < 6 for c in [int(k.replace(" ", "")[::-1][3 * i]) + 2 * int(k.replace(" ", "")[::-1][3 * i + 1])
                                          + 4 * int(k.replace(" ", "")[::-1][3 * i + 2]) for i in range(4)])
    s = success_rate(counts, compact_decoder, valid=valid)
    assert s["n_total"] == 100 and s["n_good"] == 35
    assert math.isclose(s["P"], 0.35) and math.isclose(s["se"], math.sqrt(0.35 * 0.65 / 100))
    assert set(s["objects"]) == {KNOWN, "0110 0110 0101"}
    assert s["n_invalid"] == 50
    assert success_rate(counts, compact_decoder)["n_invalid"] is None


def test_wald():
    lo, hi = wald(0.5, 100)
    assert math.isclose(lo, 0.5 - 1.96 * 0.05) and math.isclose(hi, 0.5 + 1.96 * 0.05)
    assert wald(1.0, 10) == (1.0, 1.0) and wald(0.0, 10) == (0.0, 0.0)


def test_header_matches_grading():
    text = (runtime.ROOT.parent.parent / "Resources" / "challenge-repo" / "GRADING.md")
    expected = ("| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth | Shots "
                "| P(correct tower) | Random-guess baseline | qBraid job ID |")
    assert GRADING_HEADER == expected
    if text.exists():                       # only on the team machine; the repo does not ship GRADING.md
        assert expected in text.read_text()
    assert results_table([]).splitlines()[0] == expected


def _row():
    core = QuantumCircuit(3)
    core.x(0)
    core.h(2)
    qc = runtime.prepare_safe(core)
    runtime.LAST_RUN.update(source="aer", device=runtime.AER_DEVICE, job_id="", credits=None)
    s = success_rate({KNOWN: 9, "111111111111": 1}, compact_decoder)
    return make_row("T1", "Core", "N=4 CUBES", 4, "compact 3/cube", "test", qc, 10, s, 4.88e-4, 1.54e-3,
                    p_exact=0.9, notes="unit test")


def test_make_row_fills_every_key():
    row = _row()
    assert list(row) == ROW_KEYS
    assert all(row[k] is not None for k in ROW_KEYS if k not in ("n_invalid", "credits"))
    assert row["qubits"] == 5 and row["qubits_note"] == "3 data + 2 plumbing"
    assert row["device"].startswith("local AerSimulator") and row["P"] == 0.9


def test_results_table_and_json_round_trip(tmp_path):
    row = _row()
    table = results_table([row])
    lines = table.splitlines()
    assert len(lines) == 3 and lines[2].count("|") == 11
    assert "0.9000 +- 0.0949 (exact 0.9000)" in lines[2] and "5 (3 data + 2 plumbing)" in lines[2]
    path = tmp_path / "results.json"
    report.save_results([row], str(path))
    assert report.load_results(str(path)) == [row]
    assert json.loads(path.read_text())[0]["id"] == "T1"


def test_plots_return_figures():
    import matplotlib
    matplotlib.use("Agg")
    rows = [{"id": "C0", "cx": 1000, "P": 0.05, "qubits": 14}, {"id": "C2", "cx": 8000, "P": 0.98, "qubits": 14}]
    assert report.plot_p_sweep(rows, rows, 1.5e-3) is not None
    assert report.plot_grover_curve([1, 5], lambda k: math.sin((2 * k + 1) * 0.04) ** 2, [0.01, 0.17]) is not None
    by_n = {4: rows[1], 5: {"id": "N5", "cx": 14000, "P": 0.48, "qubits": 17}}
    assert report.plot_bonus_scaling(by_n, {4: 0.985, 5: 0.479}, {4: 1.5e-3, 5: 2.6e-4}) is not None


def test_draw_tower_letters_runs():
    import matplotlib
    matplotlib.use("Agg")
    report.draw_tower_letters([("A", "B", "C", "D"), ("B", "C", "D", "E")], title="letters")
    report.draw_tower_letters(compact_decoder(KNOWN))
