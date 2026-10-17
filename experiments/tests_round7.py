"""Round-7 checks, written by the student before the noise study.
Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round7.py -q -p no:cacheprovider

make_puzzle(3, s) with the smallest seed s that has an answer, accepted recipe, p in {1,2,3,4,6}:
1. noise off: Aer P(solved) is within 3 binomial standard errors of the exact P, and every
   shot is one-hot;
2. noise on: the post-selected count equals the number of shots that decode as one-hot;
3. every reported rate recomputes from the saved counts (solved shots pass solves()).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

P_VALUES = [1, 2, 3, 4, 6]
SHOTS = 2000
TOL = 1e-9


def bitstring(choices, n_cubes):
    bits = ["0"] * (6 * n_cubes)
    for c, k in enumerate(choices):
        bits[6 * c + k] = "1"
    return "".join(reversed(bits))


# ---------------------------------------------------------------- counting on hand-made counts

def test_rates_post_select_exactly_the_one_hot_shots():
    cubes = S.CUBES   # the N = 4 puzzle, whose answers are known
    solved_pick = tuple(int(i) for i in np.argwhere(S.solved_mask(cubes))[0])
    counts = {bitstring(solved_pick, 4): 7,       # one-hot and solved
              bitstring((0, 0, 0, 0), 4): 5,      # one-hot, not solved
              "1" * 24: 3, "0" * 24: 2}           # not one-hot
    rates = S.rates_from_counts(counts, cubes)
    assert rates["shots"] == 17
    assert rates["one_hot"] == 12 and rates["post_selected_shots"] == 12
    assert rates["solved"] == 7
    assert rates["p_solved"] == pytest.approx(7 / 17)
    assert rates["one_hot_fraction"] == pytest.approx(12 / 17)
    assert rates["p_post_selected"] == pytest.approx(7 / 12)


def test_noise_model_has_the_stated_errors():
    model = S.noise_model()
    instructions = set(model.noise_instructions)
    assert {"cx", "sx", "x", "measure"} <= instructions
    assert "rz" not in instructions


# ---------------------------------------------------------------- results file

@pytest.fixture(scope="module")
def data():
    path = RESULTS / "round7.json"
    assert path.exists(), "write experiments/results/round7.json"
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def cubes(data):
    return S.starter_puzzle(3, data["puzzle_seed"])


def test_puzzle_seed_is_the_smallest_with_an_answer(data):
    count = S.load_starter()["count_answers"]
    s = data["puzzle_seed"]
    assert all(count(S.starter_puzzle(3, t)) == 0 for t in range(s))
    assert count(S.starter_puzzle(3, s)) == data["answers"] >= 1


def test_setup_matches_the_assignment(data):
    # Allowed by the assignment: drop the largest p if noisy runs are too slow, and record it.
    assert data["p_values"] + data["dropped_p"] == P_VALUES and data["shots"] == SHOTS
    assert [row["p"] for row in data["rows"]] == data["p_values"]
    assert data["seed_simulator"] == 7 and data["jitter_seed"] == 0
    assert data["objective"] == "gibbs1" and data["mixer"] == "full"
    assert not any("adopt" in key or "winner" in key or "best_p" in key for key in data)


def test_exact_p_recomputes_from_angles(data, cubes):
    costs, mask = S.cost_tensor(cubes), S.solved_mask(cubes)
    for row in data["rows"]:
        p, angles = row["p"], np.array(row["angles"])
        psi = S.qaoa_state(costs, angles[:p], angles[p:], S.MIXERS["full"])
        assert float((np.abs(psi) ** 2)[mask].sum()) == pytest.approx(row["exact_p"], abs=TOL)


def test_noiseless_aer_matches_exact_within_3_sigma(data):
    for row in data["rows"]:
        noiseless = row["noiseless"]
        sigma = math.sqrt(row["exact_p"] * (1 - row["exact_p"]) / SHOTS)
        assert abs(noiseless["p_solved"] - row["exact_p"]) <= 3 * sigma + 1e-12
        assert noiseless["one_hot"] == SHOTS


def test_every_rate_recomputes_from_saved_counts(data, cubes):
    for row in data["rows"]:
        for kind in ("noiseless", "noisy"):
            saved = row[kind]
            recomputed = S.rates_from_counts(saved["counts"], cubes)
            for key in ("shots", "one_hot", "solved", "post_selected_shots",
                        "p_solved", "one_hot_fraction", "p_post_selected"):
                assert saved[key] == pytest.approx(recomputed[key], abs=TOL)
        assert row["noisy"]["post_selected_shots"] == row["noisy"]["one_hot"]
        assert row["exact_times_fidelity"] == pytest.approx(
            row["exact_p"] * (1 - 1e-2) ** row["cx_grading"], abs=TOL)
