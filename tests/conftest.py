"""Shared test setup: repo root on sys.path, no qBraid credentials, a temporary HOME."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_configure(config):
    """Register the slow marker so `-m slow` and `-m "not slow"` work without warnings."""
    config.addinivalue_line("markers", "slow: takes more than about 20 seconds")


@pytest.fixture(autouse=True)
def _no_credentials(monkeypatch, tmp_path):
    """Hide every qBraid credential from every test: fresh HOME, no key variables."""
    monkeypatch.setenv("HOME", str(tmp_path))
    for name in ("QBRAID_API_KEY", "QBRAID_ACCESS_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(ROOT)
    yield


@pytest.fixture
def cubes_n():
    """Return a function n -> the puzzle instance with n cubes (puzzle.instance)."""
    from src.puzzle import instance
    return instance


@pytest.fixture
def angles():
    """The trained compact-QAOA angles for the 4-cube puzzle, keyed by depth p."""
    from src.compact import load_angles
    return load_angles(str(ROOT / "results" / "angles_Cc_N4.json"))
