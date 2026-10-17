"""Round-9 checks, written by the student before the noise grid.
Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round9.py -q -p no:cacheprovider

The submitted file results/hardware_n3_p1.qasm, loaded as-is (215 CX, marker on q[18]):
1. the simulated file's SHA-256 equals the one recorded in round8.json;
2. with all noise off: within 3 sigma of exact, 100% one-hot, no marker shots dropped;
3. every reported rate, expected 100-shot count, interval and p-value recomputes from
   the saved counts.
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest
from scipy.stats import binom

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
QASM = RESULTS / "hardware_n3_p1.qasm"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

GRID = {(cx, ro) for cx in (0.003, 0.005, 0.01) for ro in (0.005, 0.02)}
MIN_SHOTS, N_PRED, BASELINE = 1000, 100, 16 / 216   # assignment said 2000; see shots_note
TOL = 1e-9


@pytest.fixture(scope="module")
def round8():
    return json.loads((RESULTS / "round8.json").read_text())


@pytest.fixture(scope="module")
def data():
    path = RESULTS / "round9.json"
    assert path.exists(), "write experiments/results/round9.json"
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def cubes():
    return S.starter_puzzle(3, 0)


def test_simulated_file_is_the_submitted_file(round8, data):
    sha = hashlib.sha256(QASM.read_bytes()).hexdigest()
    assert sha == round8["qasm_sha256"] == data["qasm_sha256"]
    assert S.load_qasm(QASM).count_ops()["cx"] == data["cx_in_file"] == 215


def test_grid_is_the_stated_one(data):
    noisy = [r for r in data["rows"] if r["noise"] is not None]
    assert {(r["noise"]["cx"], r["noise"]["readout"]) for r in noisy} == GRID
    assert all(r["noise"]["sx_x"] == 5e-4 for r in noisy)
    assert data["shots"] >= MIN_SHOTS and data["shots_note"] and data["seed_simulator"] == 7
    assert data["baseline_post_selected"] == pytest.approx(BASELINE)


def test_noiseless_row_matches_exact(data, round8):
    row = next(r for r in data["rows"] if r["noise"] is None)
    exact = round8["exact_p"]
    shots = data["shots"]
    sigma = math.sqrt(exact * (1 - exact) / shots)
    assert abs(row["p_all"] - exact) <= 3 * sigma
    assert row["kept"] == shots and row["marker_dropped"] == 0


def test_every_number_recomputes_from_saved_counts(data, cubes):
    for row in data["rows"]:
        fresh = S.results_row(row["counts"], cubes, marker=True)
        for key in ("total", "kept", "solved", "marker_dropped"):
            assert row[key] == fresh[key]
        shots = fresh["total"] + fresh["marker_dropped"]
        assert shots == data["shots"]
        assert row["p_all"] == pytest.approx(fresh["solved"] / shots, abs=TOL)
        assert row["kept_fraction"] == pytest.approx(fresh["kept"] / shots, abs=TOL)
        assert row["p_post_selected"] == pytest.approx(fresh["solved"] / fresh["kept"], abs=TOL)

        pred = row["pred_100"]
        kept_rate, solved_rate = fresh["kept"] / shots, fresh["solved"] / shots
        assert pred["expected_kept"] == pytest.approx(N_PRED * kept_rate, abs=TOL)
        assert pred["expected_solved"] == pytest.approx(N_PRED * solved_rate, abs=TOL)
        assert pred["kept_95"] == [int(binom.ppf(0.025, N_PRED, kept_rate)),
                                   int(binom.ppf(0.975, N_PRED, kept_rate))]
        assert pred["solved_95"] == [int(binom.ppf(0.025, N_PRED, solved_rate)),
                                     int(binom.ppf(0.975, N_PRED, solved_rate))]
        k, s = round(pred["expected_kept"]), round(pred["expected_solved"])
        expected_p = float(binom.sf(s - 1, k, BASELINE)) if k else 1.0
        assert pred["p_value_vs_random"] == pytest.approx(expected_p, abs=1e-12)
