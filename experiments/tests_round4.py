"""Round-4 checks, written by the student before the objective change.
Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round4.py -q -p no:cacheprovider

(a) The training objective depends only on the histogram of measured costs: it never
    sees the answer list or which states are solved.
(b) Every P(solved) reported in results/round4.json recomputes from its stored angles.
"""
import inspect
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

SEEDS = [0, 1, 2, 3, 4]
TOL = 1e-9


def bitstring(choices):
    """Qiskit counts key for a legal pick (qubit 0 is the rightmost character)."""
    bits = ["0"] * (6 * len(choices))
    for c, k in enumerate(choices):
        bits[6 * c + k] = "1"
    return "".join(reversed(bits))


# ---------------------------------------------------------------- (a) histogram only

def test_objective_takes_no_answer_information():
    for fn in (S.objective_gibbs, S.cost_histogram, S.gibbs_from_histogram):
        names = set(inspect.signature(fn).parameters)
        assert not names & {"solved", "mask", "answers", "good"}


def test_counts_with_the_same_cost_histogram_score_the_same():
    costs = S.cost_tensor(S.CUBES)
    # Two different sets of legal picks, matched one-to-one by cost.
    rng = np.random.default_rng(0)
    picks = [tuple(rng.integers(0, 6, 4)) for _ in range(40)]
    swapped = []
    for pick in picks:
        same_cost = np.argwhere(costs == costs[pick])
        swapped.append(tuple(same_cost[rng.integers(len(same_cost))]))
    counts_a = {bitstring(p): i + 1 for i, p in enumerate(picks)}
    counts_b = {bitstring(p): i + 1 for i, p in enumerate(swapped)}
    hist_a, hist_b = S.cost_histogram(counts_a, S.CUBES), S.cost_histogram(counts_b, S.CUBES)
    if len(counts_a) == len(picks) and len(counts_b) == len(swapped):
        assert hist_a == hist_b
    assert S.gibbs_from_histogram(hist_a) == pytest.approx(S.gibbs_from_histogram(hist_b))


def test_exact_objective_equals_its_histogram_form():
    """The exact-state objective used for training is the same function of the cost
    histogram, so permuting probability among equal-cost states cannot change it."""
    costs = S.cost_tensor(S.CUBES)
    rng = np.random.default_rng(1)
    probs = rng.random(costs.shape)
    probs /= probs.sum()
    hist = {float(c): float(probs[costs == c].sum()) for c in np.unique(costs)}
    assert S.objective_gibbs(probs, costs) == pytest.approx(S.gibbs_from_histogram(hist))
    shuffled = probs.copy()
    for c in np.unique(costs):
        idx = np.nonzero(costs == c)
        shuffled[idx] = rng.permutation(probs[idx])
    assert S.objective_gibbs(shuffled, costs) == pytest.approx(S.objective_gibbs(probs, costs))


def test_objective_prefers_mass_at_low_cost_more_than_the_average_does():
    """Same mean cost (4), but A has weight at cost 0: Gibbs ranks A better, average ties."""
    hist_a = {0.0: 0.5, 8.0: 0.5}
    hist_b = {4.0: 1.0}
    assert sum(c * w for c, w in hist_a.items()) == sum(c * w for c, w in hist_b.items())
    assert S.gibbs_from_histogram(hist_a) < S.gibbs_from_histogram(hist_b)


def test_shots_that_are_not_one_hot_are_left_out():
    counts = {bitstring((0, 0, 0, 0)): 3, "1" * 24: 5}
    assert sum(S.cost_histogram(counts, S.CUBES).values()) == 3


# ---------------------------------------------------------------- (b) results recompute

@pytest.fixture(scope="module")
def data():
    path = RESULTS / "round4.json"
    assert path.exists(), "write experiments/results/round4.json"
    return json.loads(path.read_text())


def test_round4_changes_only_the_objective(data):
    assert data["objective"] == "gibbs1"
    assert data["mixer"] == "full"
    assert data["p"] == 7
    assert data["jitter"] == pytest.approx(0.05)
    assert [run["seed"] for run in data["runs"]] == SEEDS
    assert not any("adopt" in key or "winner" in key for key in data)


def test_every_reported_p_solved_recomputes_from_its_angles(data):
    costs, mask = S.cost_tensor(S.CUBES), S.solved_mask(S.CUBES)
    values = []
    for run in data["runs"]:
        angles = np.array(run["angles"])
        p = len(angles) // 2
        psi = S.qaoa_state(costs, angles[:p], angles[p:], S.MIXERS["full"])
        recomputed = float((np.abs(psi) ** 2)[mask].sum())
        assert recomputed == pytest.approx(run["p_solved"], abs=TOL)
        values.append(recomputed)
    assert data["median"] == pytest.approx(float(np.median(values)), abs=TOL)
    assert data["min"] == pytest.approx(min(values), abs=TOL)
    assert data["max"] == pytest.approx(max(values), abs=TOL)
    assert data["cx_grading"] > 0 and data["depth_grading"] > 0
