"""Round-6 checks, written by the student before the depth sweep.
Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round6.py -q -p no:cacheprovider

Accepted recipe on N = 4, p = 1..10, seeds 0, 1, 2:
1. every (seed, p) P(solved) recomputes from that p's stored angles;
2. the per-p median/min/max come from exactly those runs;
3. the recorded p = 7 drift from round4.json recomputes (equality is not required).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

SEEDS = [0, 1, 2]
P_VALUES = list(range(1, 11))
TOL = 1e-9


@pytest.fixture(scope="module")
def data():
    path = RESULTS / "round6.json"
    assert path.exists(), "write experiments/results/round6.json"
    return json.loads(path.read_text())


def test_sweep_uses_the_accepted_recipe(data):
    assert data["objective"] == "gibbs1" and data["mixer"] == "full"
    assert data["hamiltonian"] == "reduced_best"
    assert data["jitter"] == pytest.approx(0.05)
    assert data["seeds"] == SEEDS and data["p_values"] == P_VALUES
    assert sorted((r["seed"], r["p"]) for r in data["runs"]) == \
        sorted((s, p) for s in SEEDS for p in P_VALUES)
    assert not any("adopt" in key or "winner" in key or "best_p" in key for key in data)


def test_every_seed_p_recomputes_from_its_angles(data):
    costs, mask = S.cost_tensor(S.CUBES), S.solved_mask(S.CUBES)
    for run in data["runs"]:
        angles = np.array(run["angles"])
        assert len(angles) == 2 * run["p"]
        p = run["p"]
        psi = S.qaoa_state(costs, angles[:p], angles[p:], S.MIXERS["full"])
        assert float((np.abs(psi) ** 2)[mask].sum()) == pytest.approx(run["p_solved"], abs=TOL)


def test_per_p_summary_comes_from_the_runs(data):
    for p in P_VALUES:
        values = [r["p_solved"] for r in data["runs"] if r["p"] == p]
        block = data["per_p"][str(p)]
        assert len(values) == len(SEEDS)
        assert block["median"] == pytest.approx(float(np.median(values)), abs=TOL)
        assert block["min"] == pytest.approx(min(values), abs=TOL)
        assert block["max"] == pytest.approx(max(values), abs=TOL)
        assert block["cx_grading"] > 0 and block["depth_grading"] > 0


def test_p7_drift_from_round4_is_recorded_honestly(data):
    round4 = {r["seed"]: np.array(r["angles"])
              for r in json.loads((RESULTS / "round4.json").read_text())["runs"]}
    for seed in SEEDS:
        mine = np.array(next(r["angles"] for r in data["runs"]
                             if r["seed"] == seed and r["p"] == 7))
        assert data["p7_drift_vs_round4"][str(seed)] == pytest.approx(
            float(np.max(np.abs(mine - round4[seed]))), abs=1e-12)
