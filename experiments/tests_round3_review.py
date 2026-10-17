"""Teacher's round-3 checks: full vs ring XY mixer, nothing else changed.
Written by the teacher; the student must not edit this file. Run from the repo root:
    .venv\\Scripts\\python.exe -m pytest experiments/tests_round3_review.py -q -p no:cacheprovider

Expected results/round3.json layout:
{
  "objective": "average",
  "hamiltonian": "<the reduced_hamiltonian gauge used for CX/depth>",
  "jitter": 0.05,
  "p": 7,
  "mixers": {
    "full": {"runs": [{"seed": 0, "p_solved": ..., "angles": [...]}, ...],
             "median": ..., "min": ..., "max": ..., "cx_grading": ..., "depth_grading": ...},
    "ring": {...same keys...}
  }
}
No winner is picked in the file; the review decides.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
sys.path.insert(0, str(HERE))

import solver as S  # noqa: E402

SEEDS = [0, 1, 2, 3, 4]
MIXER_NAMES = ["full", "ring"]
TOL = 1e-9


@pytest.fixture(scope="module")
def data():
    path = RESULTS / "round3.json"
    assert path.exists(), "write experiments/results/round3.json"
    return json.loads(path.read_text())


def test_only_the_mixer_changes(data):
    assert data["objective"] == "average"
    assert data["p"] == 7
    assert data["jitter"] == pytest.approx(0.05)
    assert sorted(data["mixers"]) == MIXER_NAMES
    assert not any("adopt" in key or "winner" in key for key in data), "the review decides"


@pytest.mark.parametrize("mixer", MIXER_NAMES)
def test_same_seeds_for_both_mixers(data, mixer):
    assert [run["seed"] for run in data["mixers"][mixer]["runs"]] == SEEDS


@pytest.mark.parametrize("mixer", MIXER_NAMES)
def test_reported_p_solved_recomputes_from_stored_angles(data, mixer):
    costs, mask = S.cost_tensor(S.CUBES), S.solved_mask(S.CUBES)
    for run in data["mixers"][mixer]["runs"]:
        angles = np.array(run["angles"])
        p = len(angles) // 2
        psi = S.qaoa_state(costs, angles[:p], angles[p:], S.MIXERS[mixer])
        assert float((np.abs(psi) ** 2)[mask].sum()) == pytest.approx(run["p_solved"], abs=TOL)


@pytest.mark.parametrize("mixer", MIXER_NAMES)
def test_median_min_max_match_the_runs(data, mixer):
    block = data["mixers"][mixer]
    values = [run["p_solved"] for run in block["runs"]]
    assert block["median"] == pytest.approx(float(np.median(values)), abs=TOL)
    assert block["min"] == pytest.approx(min(values), abs=TOL)
    assert block["max"] == pytest.approx(max(values), abs=TOL)
    assert block["cx_grading"] > 0 and block["depth_grading"] > 0


def test_round3_note_explains_the_round():
    """results/round3_note.md: at least four sentences in the student's own words."""
    note = RESULTS / "round3_note.md"
    assert note.exists(), "write experiments/results/round3_note.md"
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", note.read_text(encoding="utf-8").strip())
                 if len(s.split()) >= 5]
    assert len(sentences) >= 4
