"""Check a submitted qBraid job and, once it has finished, record its result. Never resubmits.

Usage (from the repo root, with QBRAID_API_KEY set for the account that owns the job):
    .venv\\Scripts\\python.exe experiments\\fetch_job.py <job_id> <label>

While the job is queued or running this prints its status and exits. When it is COMPLETED it
processes the counts exactly like qbraid_job.py (marker split, one-hot post-selection, solves())
and writes experiments/results/qbraid_<label>.json.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / "experiments"), str(REPO)]

import solver  # noqa: E402
from qbraid.runtime import QbraidJob  # noqa: E402

RANDOM_POST_SELECTED = 16 / 216


def main(job_id, label):
    job = QbraidJob(job_id)
    status = job.status()
    print(f"{job_id}: {status.name}")
    if status.name != "COMPLETED":
        return
    counts = job.result().data.get_counts()
    cubes = json.loads((REPO / "experiments" / "results" / "round7.json").read_text())["cubes"]
    row = solver.results_row(counts, cubes, marker=True, device=job_id.split("-8876-")[0].split("-d8ed-")[0],
                             label=label)
    row.update(job_id=job_id, random_post_selected=RANDOM_POST_SELECTED, raw_counts=counts)
    out = REPO / "experiments" / "results" / f"qbraid_{label}.json"
    out.write_text(json.dumps(row, indent=1))
    print(f"kept {row['kept']}/{row['total']} one-hot shots (marker dropped {row['marker_dropped']}); "
          f"solved {row['solved']}  ->  P(all) {row['p_all']:.2%}, "
          f"P(post-selected) {row['p_post_selected']:.2%} vs random {RANDOM_POST_SELECTED:.2%}")
    print("saved", out)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
