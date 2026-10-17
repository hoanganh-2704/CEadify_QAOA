"""Turning counts into checked numbers: success rates, results-table rows, results.json and figures."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from resources.helpers import AMBER, GREY, PAINT, TEAL, VIOLET, draw_tower, show
from src import runtime

GRADING_HEADER = ("| Puzzle (N cubes) | Encoding | Device | Qubits | Two-qubit gates (after transpiling) | Depth "
                  "| Shots | P(correct tower) | Random-guess baseline | qBraid job ID |")
GRADING_RULE = "|---|---|---|---|---|---|---|---|---|---|"
ROW_KEYS = ["id", "level", "puzzle", "N", "encoding", "algorithm", "device", "qubits", "qubits_note", "cx", "depth",
            "shots", "n_good", "n_invalid", "P", "P_se", "P_exact", "baseline_bits", "baseline_subspace", "job_id",
            "credits", "notes"]


# Human-readable experiment names; the short code (C2, G1, ...) stays in parentheses for traceability.
# "rounds" = QAOA layers p, "steps" = Grover iterations K: both are the depth of the circuit.
_W = "4-cube warm-up (front/back only)"
_T = "4-cube tower"
_B = "Bonus N-cube tower"        # N is replaced by the row's number of cubes
LABELS = {
    "W1p1": f"{_W}, QAOA 1 round", "W1": f"{_W}, QAOA 2 rounds",
    "C0": f"{_T}, QAOA 3 rounds", "C1": f"{_T}, QAOA 12 rounds", "C2": f"{_T}, QAOA 24 rounds",
    "C3": f"{_T}, QAOA 24 rounds, angles from another puzzle", "C4": f"{_T}, QAOA 3 rounds, CVaR-trained angles",
    "C5": f"{_T}, QAOA 24 rounds, 2-number ramp (tuned on N=4)",
    "G0": f"{_T}, Grover 5 steps", "G1": f"{_T}, Grover 10 steps", "G2": f"{_T}, Grover 19 steps",
    "B1": f"{_T}, starter 24-qubit encoding, QAOA 3 rounds",
    **{f"N{n}": f"{_B}, QAOA 24 rounds (4-cube angles)" for n in (5, 6, 7, 8)},
}
# the QPU job tags of scripts/run_qpu.py ("G1" there is Grover with 1 step, not the simulator row G1 = 10 steps)
QPU_LABELS = {"W1p1": f"{_W}, QAOA 1 round", "G1": f"{_T}, Grover 1 step", "Cc1": f"{_T}, QAOA 1 round",
              "G1N5": f"{_B}, Grover 1 step", "C2": LABELS["C2"], "G2": LABELS["G2"], "N5": LABELS["N5"]}


def label_of(row):
    """The human-readable experiment name of a row (stored label, else looked up from its id)."""
    if row.get("label"):
        return row["label"]
    rid = row["id"]
    label = QPU_LABELS.get(rid[:-4], rid) if rid.endswith("-QPU") else LABELS.get(rid.split("-")[0], rid)
    return label.replace("N-cube", f"{row['N']}-cube")


# ---------------------------------------------------------------- success rates

def success_rate(counts, decoder, valid=None):
    """Fraction of shots whose decoded object is truthy; decoder(key) must return None unless the tower is verified."""
    n_total = sum(counts.values())
    n_good, n_invalid, objects = 0, 0, {}
    for key, n in counts.items():
        obj = decoder(key)
        if obj:
            n_good += n
            objects[key] = obj
        if valid is not None and not valid(key):
            n_invalid += n
    p = n_good / n_total if n_total else 0.0
    se = math.sqrt(p * (1 - p) / n_total) if n_total else 0.0
    return {"n_good": n_good, "n_total": n_total, "P": p, "se": se, "objects": objects,
            "n_invalid": n_invalid if valid is not None else None}


def compact_valid(key):
    """True when every 3-bit block of a compact key is a real code (0..5, not 6 or 7)."""
    from src.compact import codes_from_key
    key = key.replace(" ", "")
    return all(k < 6 for k in codes_from_key(key, len(key) // 3))


def onehot_valid(key):
    """True when a one-hot key (6 qubits per cube) decodes to a legal choice: every 3-bit triple has exactly one 1
    and the two triples of a cube pick different pairs (a same-pair overlap is rejected too, like decode_onehot)."""
    from src.warmup import decode_onehot
    key = key.replace(" ", "")
    return decode_onehot(key, len(key) // 6) is not None


def frontback_valid(key):
    """True when every 3-bit triple of a front/back key (3 qubits per cube) has exactly one 1."""
    from src.warmup import decode_frontback
    key = key.replace(" ", "")
    return decode_frontback(key, len(key) // 3) is not None


def wald(p, n):
    """95 % Wald interval (low, high) for a success rate p measured on n shots, clipped to [0, 1]."""
    half = 1.96 * math.sqrt(p * (1 - p) / n) if n else 0.0
    return max(0.0, p - half), min(1.0, p + half)


# ---------------------------------------------------------------- rows and the table

def make_row(rid, level, puzzle, n, encoding, algorithm, qc_prepared, shots, success, baseline_bits,
             baseline_subspace, p_exact=None, job_id="", notes="", qubits_note=None):
    """One results-table row; gate counts come from the prepared circuit, device and job from runtime.LAST_RUN."""
    m = runtime.circuit_metrics(qc_prepared)
    run = runtime.LAST_RUN
    return {"id": rid, "level": level, "puzzle": puzzle, "N": int(n), "encoding": encoding, "algorithm": algorithm,
            "device": run["device"] or runtime.AER_DEVICE, "qubits": int(m["qubits"]),
            "qubits_note": qubits_note or f"{m['qubits'] - 2} data + 2 plumbing",
            "cx": int(m["cx"]), "depth": int(m["depth"]), "shots": int(shots),
            "n_good": success["n_good"], "n_invalid": success.get("n_invalid"),
            "P": float(success["P"]), "P_se": float(success["se"]),
            "P_exact": None if p_exact is None else float(p_exact),
            "baseline_bits": float(baseline_bits), "baseline_subspace": float(baseline_subspace),
            "job_id": job_id or run.get("job_id") or "", "credits": run.get("credits"), "notes": notes}


def _cell_p(row):
    """P(correct tower) cell: sampled value +- standard error, then the exact value when known."""
    text = f"{row['P']:.4f} +- {row['P_se']:.4f}"
    if row.get("P_exact") is not None:
        text += f" (exact {row['P_exact']:.4f})"
    return text


def _cell_job(row):
    """qBraid job ID cell: the job id and its cost in credits when known, or 'none (local run)'."""
    if not row.get("job_id"):
        return "none (local run)"
    if row.get("credits") is None:
        return row["job_id"]
    return f"{row['job_id']} ({row['credits']:g} credits)"


def results_table(rows):
    """Markdown table with the ten GRADING.md columns, one line per row."""
    lines = [GRADING_HEADER, GRADING_RULE]
    for r in rows:
        cells = [f"{label_of(r)} ({r['id']}): {r['puzzle']}", f"{r['encoding']}, {r['algorithm']}", r["device"],
                 f"{r['qubits']} ({r['qubits_note']})", f"{r['cx']:,}", f"{r['depth']:,}", f"{r['shots']:,}",
                 _cell_p(r), f"{r['baseline_bits']:.2e} (any {r['qubits'] - 2}-bit string) / {r['baseline_subspace']:.2e} "
                 + ("(W x W start subspace)" if r["encoding"].startswith("starter one-hot") else "(random valid placements)"),
                 _cell_job(r)]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    return "\n".join(lines)


def _pct(x, se=None):
    """A probability as a percent with sensible digits: 2 decimals above 99 % (so 99.85 % is not shown as 99.9 %),
    two significant figures for tiny baselines, 1 decimal otherwise; '+- se' in the same units when given."""
    if x is None:
        return ""
    v = 100 * x
    if v == 0 or v >= 1:
        d = 2 if v >= 99 or (se is not None and 0 < 100 * se < 0.1) else 1
        txt = f"{v:.{d}f}"
    else:
        d = None
        txt = f"{v:.2g}"
    if se is not None:
        txt += f" +- {100 * se:.{d if d is not None else 2}f}"
    return txt + " %"


def comparison_table(rows):
    """One line per circuit: name, two-qubit gates, noiseless (exact) P, qBraid SV1 P, Rigetti QPU P, random guess.
    Simulator, SV1 and QPU rows of the same circuit (same name and N) share a line; missing runs stay blank."""
    lines = ["| Experiment | Two-qubit gates | Perfect simulator | qBraid SV1 | Rigetti QPU | Random valid placements "
             "| Any 12-bit string |", "|---|---|---|---|---|---|---|"]
    groups = {}
    for r in rows:
        key = (label_of(r), int(r["N"]))
        g = groups.setdefault(key, {"ids": [], "cx": r["cx"], "exact": None, "sv1": None, "qpu": None,
                                    "random": r["baseline_subspace"], "random_bits": r["baseline_bits"],
                                    "bits": r["qubits"] - 2})
        g["ids"].append(r["id"])
        if r["id"].endswith("-SV1"):
            g["sv1"] = r
        elif r["id"].endswith("-QPU"):
            g["qpu"] = r
        if g["exact"] is None and r.get("P_exact") is not None:
            g["exact"] = r["P_exact"]
    for (label, n), g in groups.items():
        name = label
        sv1 = "" if g["sv1"] is None else _pct(g["sv1"]["P"], g["sv1"]["P_se"])
        q = g["qpu"]
        qpu = "" if q is None else (f"{_pct(q['P'], q['P_se'])} ({q['n_good']}/{q['shots']}); valid readings "
                                    + _pct(1 - (q["n_invalid"] or 0) / q["shots"]))
        lines.append(f"| {name} ({', '.join(g['ids'])}) | {g['cx']:,} | {_pct(g['exact'])} | {sv1} | {qpu} "
                     f"| {_pct(g['random'])} | {_pct(g['random_bits'])}"
                     + ("" if g["bits"] == 12 else f" ({g['bits']}-bit)") + " |")
    return "\n".join(lines)


README_IDS = ["C0", "C1", "C2", "C2-SV1", "C2-QPU", "G0", "G1", "G1-QPU", "G2", "G2-SV1", "G2-QPU", "B1",
              "N5", "N5-SV1", "G1N5-QPU", "N6", "N7", "N8"]


def readme_rows(rows):
    """The rows shown in the README tables: the N = 4 tower rows, the Bonus rows and their SV1 / QPU twins
    (the warm-up and the C3-C5 variants stay in the notebook and results/results_table_all.md)."""
    keep = [r for r in rows if r["id"] in README_IDS]
    return sorted(keep, key=lambda r: README_IDS.index(r["id"]))


def _jsonable(x):
    """Convert numpy scalars and arrays so json.dump accepts them."""
    if isinstance(x, np.generic):
        return x.item()
    if isinstance(x, np.ndarray):
        return x.tolist()
    return str(x)


def save_results(rows, path="results/results.json"):
    """Write the rows (a list of dicts) to a JSON file, without the decoded objects."""
    path = runtime._path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(rows), indent=1, default=_jsonable))


def load_results(path="results/results.json"):
    """Read rows back from a results JSON file (a list, or a dict with a "rows" key)."""
    data = json.loads(runtime._path(path).read_text())
    return data["rows"] if isinstance(data, dict) else data


def timestamp():
    """Current UTC time as an ISO string, for provenance fields."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- figures (each returns a matplotlib figure)

def plot_p_sweep(rows_cc, rows_grover, baseline):
    """P(correct tower) against CX count for compact QAOA and Grover rows, with the random-guess line."""
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for rows, colour, label in ((rows_cc, VIOLET, "compact QAOA (p layers)"), (rows_grover, TEAL, "Grover (K iterations)")):
        rows = sorted(rows, key=lambda r: r["cx"])
        if rows:
            ax.plot([r["cx"] for r in rows], [r["P"] for r in rows], "o-", color=colour, label=label)
            for r in rows:
                ax.annotate(r["id"], (r["cx"], r["P"]), textcoords="offset points", xytext=(4, -10), fontsize=8,
                            color=colour)
    ax.axhline(baseline, color=AMBER, ls="--", lw=1, label=f"random guess {baseline:.1e}")
    ax.set_xlabel("two-qubit gates (CX after transpiling)")
    ax.set_ylabel("P(correct tower)")
    ax.set_ylim(-0.02, 1.05)
    ax.set_title("4 cubes, 12 data qubits: success against gate cost", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="center right")
    return fig


def plot_grover_curve(ks, theory, sampled):
    """Grover success against iterations K: the sin^2 law (line) and measured values (dots)."""
    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    if callable(theory):
        grid = np.arange(0, max(ks) + 2)
        ax.plot(grid, [theory(k) for k in grid], color=VIOLET, label="theory sin^2((2K+1) theta)")
    else:
        ax.plot(ks, theory, "-", color=VIOLET, label="theory sin^2((2K+1) theta)")
    ax.plot(ks, sampled, "o", color=AMBER, label="sampled (Aer)")
    ax.set_xlabel("Grover iterations K")
    ax.set_ylabel("P(correct tower)")
    ax.set_ylim(-0.02, 1.05)
    ax.set_title("Grover on 6^4 = 1,296 valid codes, M = 2 answers", fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    return fig


def plot_bonus_scaling(rows_by_n, exact_by_n, baselines):
    """Three panels against N: submitted qubits, CX count, and P (log scale) with the random-guess baseline."""
    ns = sorted(rows_by_n)
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.2))
    axes[0].plot(ns, [rows_by_n[n]["qubits"] for n in ns], "o-", color=VIOLET)
    axes[0].set_ylabel("qubits submitted")
    axes[1].plot(ns, [rows_by_n[n]["cx"] for n in ns], "o-", color=TEAL)
    axes[1].set_ylabel("CX after transpiling")
    axes[2].semilogy(ns, [max(rows_by_n[n]["P"], 1e-9) for n in ns], "o", color=AMBER, label="sampled")
    ex = sorted(exact_by_n)
    axes[2].semilogy(ex, [exact_by_n[n] for n in ex], "-", color=VIOLET, label="exact")
    bn = sorted(baselines)
    axes[2].semilogy(bn, [baselines[n] for n in bn], "--", color=GREY, label="random guess (valid codes)")
    axes[2].set_ylabel("P(correct tower)")
    axes[2].legend(frameon=False, fontsize=8)
    for ax in axes:
        ax.set_xlabel("N cubes = N colours")
        ax.set_xticks(sorted(set(ns) | set(ex) | set(bn)))
    fig.suptitle("Bonus: the same p = 24 angles (trained at N = 4) on N cubes", fontsize=10, color=GREY)
    fig.tight_layout()
    return fig


def _letter_colour(letter):
    """A fill colour for any colour letter: the starter paint for R, G, B, Y, a fixed palette otherwise."""
    extra = ["#8B5CF6", "#0E9488", "#C2772A", "#DB4B92", "#3B82F6", "#2FA95F", "#D64545", "#E8B400"]
    return PAINT.get(letter) or extra[(ord(letter) - ord("A")) % len(extra)]


def draw_tower_letters(tower, title=""):
    """Draw a tower of (front, right, back, left) letters; uses helpers.draw_tower when the letters are R, G, B, Y."""
    if all(ch in PAINT for view in tower for ch in view) and not title:
        draw_tower(tower)
        return
    fig, ax = plt.subplots(figsize=(4.4, 0.8 * len(tower) + 0.8))
    for row, view in enumerate(reversed(tower)):
        for col, colour in enumerate(view):
            ax.add_patch(Rectangle((col * 1.15, row), 0.95, 0.95, facecolor=_letter_colour(colour),
                                   edgecolor="white", linewidth=2))
            ax.text(col * 1.15 + 0.47, row + 0.47, colour, ha="center", va="center", color="white",
                    fontsize=11, fontweight="bold")
    for col, name in enumerate(["front", "right", "back", "left"]):
        ax.text(col * 1.15 + 0.47, len(tower) + 0.1, name, ha="center", fontsize=9)
    ax.set_xlim(-0.1, 4.6)
    ax.set_ylim(-0.1, len(tower) + 0.5)
    ax.set_aspect("equal")
    ax.axis("off")
    if title:
        ax.set_title(title, fontsize=10)
    show(fig)


def save_figure(fig, name):
    """Save a figure as results/figures/<name>.png and return the path."""
    path = runtime._path("results/figures") / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=130, bbox_inches="tight")
    return Path(path)
