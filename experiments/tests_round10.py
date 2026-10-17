"""Round-10 checks, written by the student before the Grover study (part (a) only).
Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round10.py -q -p no:cacheprovider

1. the ideal oracle marks exactly the picks an independent solves() brute force finds,
   and their number equals the starter's count_answers;
2. simulated P(solved) after k iterations equals sin^2((2k+1) theta), sin^2 theta = M / 6^N,
   to 1e-9 for every reported k;
3. every number recomputes from saved data; QAOA values are read from round6/round7 json.
"""
import itertools
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

TOL = 1e-9
PUZZLES = {"3": lambda: S.starter_puzzle(3, 0), "4": lambda: S.CUBES}


@pytest.fixture(scope="module")
def data():
    path = RESULTS / "round10.json"
    assert path.exists(), "write experiments/results/round10.json"
    return json.loads(path.read_text())


@pytest.mark.parametrize("n", sorted(PUZZLES))
def test_oracle_marks_exactly_the_brute_force_solutions(n):
    cubes = PUZZLES[n]()
    marked = {tuple(int(i) for i in idx) for idx in np.argwhere(S.grover_oracle_mask(cubes))}
    solves = S.load_starter()["solves"]
    brute = {pick for pick in itertools.product(range(6), repeat=len(cubes))
             if solves(S.tower_of(cubes, pick))}
    assert marked == brute
    assert len(marked) == S.load_starter()["count_answers"](cubes)


@pytest.mark.parametrize("n", sorted(PUZZLES))
def test_grover_curve_matches_the_formula_and_recomputes(data, n):
    block = data["grover"][n]
    cubes = PUZZLES[n]()
    mask = S.grover_oracle_mask(cubes)
    m, d = int(mask.sum()), 6 ** len(cubes)
    assert (block["M"], block["legal_picks"]) == (m, d)
    theta = math.asin(math.sqrt(m / d))
    curve = S.grover_curve(mask, len(block["p_solved"]) - 1)
    for k, p in enumerate(block["p_solved"]):
        assert p == pytest.approx(math.sin((2 * k + 1) * theta) ** 2, abs=TOL)
        assert p == pytest.approx(curve[k], abs=TOL)
    best = int(np.argmax(block["p_solved"]))
    assert block["best_k"] == best and block["oracle_calls_at_best"] == best
    assert block["p_best"] == pytest.approx(block["p_solved"][best], abs=TOL)
    assert block["random_legal"] == pytest.approx(m / d, abs=TOL)
    assert len(block["p_solved"]) - 1 > best        # reported a little past the first peak


def test_qaoa_comparison_is_read_from_saved_results(data):
    r6 = json.loads((RESULTS / "round6.json").read_text())["per_p"]
    r7 = {row["p"]: row for row in json.loads((RESULTS / "round7.json").read_text())["rows"]}
    for p, value in data["qaoa"]["4"].items():
        assert value["p_solved"] == pytest.approx(r6[p]["median"], abs=TOL)
        assert value["cx_grading"] == r6[p]["cx_grading"]
    for p, value in data["qaoa"]["3"].items():
        assert value["p_solved"] == pytest.approx(r7[int(p)]["exact_p"], abs=TOL)
        assert value["cx_grading"] == r7[int(p)]["cx_grading"]


def test_part_b_skip_is_recorded(data):
    assert data["part_b"] == "skipped"
