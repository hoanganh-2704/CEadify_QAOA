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


def results_table(rows):
    """Markdown table with the ten GRADING.md columns, one line per row."""
    lines = [GRADING_HEADER, GRADING_RULE]
    for r in rows:
        cells = [f"{r['id']}: {r['puzzle']}", f"{r['encoding']}, {r['algorithm']}", r["device"],
                 f"{r['qubits']} ({r['qubits_note']})", f"{r['cx']:,}", f"{r['depth']:,}", f"{r['shots']:,}",
                 _cell_p(r), f"{r['baseline_bits']:.2e} (any bitstring) / {r['baseline_subspace']:.2e} "
                 + ("(W x W start subspace)" if r["encoding"].startswith("starter one-hot") else "(valid codes)"),
                 r["job_id"] or "none (local run)"]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    return "\n".join(lines)


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
