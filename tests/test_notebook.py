"""Slow end-to-end check: the whole notebook runs headless on a temporary copy of the repo (pytest -m slow)."""
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.slow
def test_notebook_runs_top_to_bottom(tmp_path):
    """jupyter nbconvert --execute of solution.ipynb in a copy of the repo exits 0 in under 10 minutes."""
    work = tmp_path / "repo"
    shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"))
    start = time.perf_counter()
    done = subprocess.run([sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
                           "--output", str(tmp_path / "out.ipynb"), "--ExecutePreprocessor.timeout=900",
                           "solution.ipynb"], cwd=work, capture_output=True, text=True, timeout=900)
    assert done.returncode == 0, done.stderr[-3000:]
    assert time.perf_counter() - start < 600
    assert (work / "results" / "results.json").exists()
