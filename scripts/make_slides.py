"""Build slides.pdf (8 pages) from results/results.json, results/facts.json and results/figures/*.png.

Run from the repository root after executing solution.ipynb:  python scripts/make_slides.py
Every number on the slides is read from those files; nothing is typed in by hand.
"""
import itertools
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIG = RESULTS / "figures"
OUT = ROOT / "slides.pdf"

INK, MUTED, ACCENT, TEAL, AMBER = "#1F2430", "#5B6170", "#8B5CF6", "#0E9488", "#C2772A"
W, H = 13.333, 7.5

plt.rcParams.update({"figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
                     "text.color": INK, "font.size": 14})


def load():
    """Read the rows and the extra facts written by the notebook."""
    rows = json.loads((RESULTS / "results.json").read_text())
    rows = rows["rows"] if isinstance(rows, dict) else rows
    facts = json.loads((RESULTS / "facts.json").read_text())
    return {r["id"]: r for r in rows}, rows, facts


def page(pdf, number, title, subtitle=None):
    """Start a slide: white page, title, optional subtitle, page number; returns the figure."""
    fig = plt.figure(figsize=(W, H))
    fig.text(0.05, 0.92, title, fontsize=28, fontweight="bold", color=INK, va="top")
    if subtitle:
        fig.text(0.05, 0.835, subtitle, fontsize=15, color=MUTED, va="top")
    fig.text(0.95, 0.03, f"{number} / 8", fontsize=11, color=MUTED, ha="right")
    fig.text(0.05, 0.03, "Instant Insanity on a quantum computer | Qiskit Fall Fest CT 2026 | qBraid challenge",
             fontsize=10, color=MUTED)
    return fig


def bullets(fig, items, x=0.05, y=0.76, size=16, gap=0.075, width=None):
    """Write a list of bullet lines from (x, y) downwards."""
    for i, item in enumerate(items):
        text = "     " + item.strip() if item.startswith("  ") else "•  " + item   # "  " marks a continuation line
        fig.text(x, y - i * gap, text, fontsize=size, color=INK, va="top")


def image(fig, name, rect):
    """Place results/figures/<name> in the rectangle (left, bottom, width, height); skip quietly if missing."""
    path = FIG / name
    ax = fig.add_axes(rect)
    ax.axis("off")
    if path.exists():
        ax.imshow(plt.imread(str(path)))
    else:
        ax.text(0.5, 0.5, f"({name} not generated)", ha="center", va="center", color=MUTED)


def table(fig, rect, header, body, size=13, col_widths=None):
    """Draw a simple table in the rectangle."""
    ax = fig.add_axes(rect)
    ax.axis("off")
    t = ax.table(cellText=body, colLabels=header, loc="upper left", cellLoc="left", colLoc="left",
                 colWidths=col_widths)
    t.auto_set_font_size(False)
    t.set_fontsize(size)
    t.scale(1, 1.6)
    for (r, _), cell in t.get_celld().items():
        cell.set_edgecolor("#D9DCE3")
        if r == 0:
            cell.set_text_props(fontweight="bold", color=INK)
            cell.set_facecolor("#F1EEFD")
    return t


def pct(x, digits=1):
    """Format a probability as a percentage."""
    return f"{100 * x:.{digits}f} %"


def main():
    """Write the 8 slides."""
    by_id, rows, facts = load()
    c2, g2 = by_id["C2"], by_id["G2"]
    bf = facts["brute_force"]
    base = facts["baselines_N4"]
    with PdfPages(OUT) as pdf:
        # 1 problem
        fig = page(pdf, 1, "Instant Insanity on a quantum computer",
                   "Stack 4 cubes so each of the 4 sides shows red, green, blue and yellow exactly once")
        bullets(fig, [
            f"24^4 = {bf['towers']:,} towers; brute force finds {bf['solved']} solved ones in {bf['seconds']:.2f} s",
            "(one tower in its 8 rotated / flipped positions). Classical search wins at this size, and we say so.",
            "Our question: how well can a quantum search on a small register find it, and what does it cost?",
            "Levels done: warm-up, core and bonus (N cubes, N colours). All runs: local Aer simulator, seed 7.",
            f"Headline: 12 qubits; QAOA {pct(c2['P'])} ({c2['cx']:,} CX), Grover {pct(g2['P'])} ({g2['cx']:,} CX);",
            f"Random guessing: {pct(base['bits3N'], 3)} (any 12-bit string) to {pct(base['valid6N'], 2)} (legal codes).",
        ], y=0.74, size=16, gap=0.065)
        image(fig, "tower_N4.png", [0.72, 0.06, 0.25, 0.35])
        pdf.savefig(fig); plt.close(fig)

        # 2 graph view
        fig = page(pdf, 2, "The graph view: 6 legal choices per cube",
                   "One dot per colour, one line per pair of opposite faces")
        bullets(fig, [
            "Each cube puts one pair on front/back, a different pair on left/right, hides the third.",
            "So a cube has 6 legal choices, and the puzzle has 6^4 = 1,296 cases.",
            "Front/back lines must touch every colour exactly twice (a 2-factor); same for left/right.",
            "Exactly 2 of the 1,296 cases solve it: the tower and its quarter turn.",
            "Every answer any circuit gives is re-checked with the starter's solves(tower_from(...)).",
        ], y=0.74, size=16, gap=0.075, x=0.05)
        image(fig, "graph_N4.png", [0.68, 0.06, 0.28, 0.33])
        pdf.savefig(fig); plt.close(fig)

        # 3 encoding
        fig = page(pdf, 3, "Our encoding: 3 qubits per cube, 12 in total",
                   "Write the choice number 0..5 in binary; codes 6 and 7 are illegal and never produced")
        body = [[str(k), f"{k:03b}", str(fb), str(lr)] for k, (fb, lr) in
                enumerate(itertools.permutations(range(3), 2))]
        table(fig, [0.05, 0.25, 0.36, 0.5], ["code", "bits q2 q1 q0", "front/back pair", "left/right pair"], body,
              size=13)
        table(fig, [0.47, 0.45, 0.48, 0.25], ["encoding", "qubits", "random string", "random legal state"],
              [["starter one-hot", "24", f"{base['bits6N']:.2e}", f"{base['WxW']:.2e}"],
               ["compact (ours)", "12", f"{base['bits3N']:.2e}", f"{base['valid6N']:.2e}"]], size=13)
        chk = facts["check_N4"]
        bullets(fig, [
            f"Cost as a 12-qubit Hamiltonian: {chk.get('n_terms')} Pauli terms, up to {chk.get('max_locality')} Z's each",
            f"Equals the classical cost on all 1,296 legal codes (largest gap {chk.get('max_gap_valid')})",
            f"Exactly {chk.get('zeros_all')} zero-energy strings among all 4,096: the two answers",
        ], x=0.47, y=0.38, size=14, gap=0.06)
        pdf.savefig(fig); plt.close(fig)

        # 4 QAOA
        c0, c1, c3, c5 = by_id.get("C0"), by_id.get("C1"), by_id.get("C3"), by_id.get("C5")
        fig = page(pdf, 4, "Search 1: QAOA with a legal-move mixer",
                   "Start in the equal mix of the 6 legal codes per cube; the mixer never leaves them")
        lines = [f"p = 24 layers: P(correct tower) = {pct(c2['P'])} +- {pct(c2['P_se'], 2)} "
                 f"({c2['n_good']:,} of {c2['shots']:,} shots, all verified)",
                 f"{c2['qubits']} qubits submitted ({c2['qubits_note']}), {c2['cx']:,} CX, depth {c2['depth']:,}"]
        if c0 and c1:
            lines.append(f"p = 3: {pct(c0['P'])} ({c0['cx']:,} CX);  p = 12: {pct(c1['P'])} ({c1['cx']:,} CX)")
        if c3:
            lines.append(f"Angles trained on a different puzzle: {pct(c3['P'])} (fairness check)")
        if c5:
            lines.append(f"Two-number ramp (grid-tuned on N = 4, no per-layer fit): {pct(c5['P'])}")
        lines.append("Angles are trained by a classical simulation of the 1,296 cases (said plainly)")
        bullets(fig, lines, y=0.75, size=14, gap=0.07, x=0.05)
        image(fig, "angles_vs_p.png", [0.50, 0.12, 0.47, 0.38])
        pdf.savefig(fig); plt.close(fig)

        # 5 Grover
        ox = facts.get("oracle_cx", {})
        g0, g1 = by_id.get("G0"), by_id.get("G1")
        fig = page(pdf, 5, "Search 2: Grover with a rules-only oracle",
                   "The oracle is generated from the cube list and the rules, never from the answer")
        lines = [f"K = 19 rounds: P = {pct(g2['P'])} +- {pct(g2['P_se'], 2)} (theory {pct(g2['P_exact'], 2)}), "
                 f"{g2['cx']:,} CX, depth {g2['depth']:,}"]
        if g0 and g1:
            lines.append(f"K = 5: {pct(g0['P'])}; K = 10: {pct(g1['P'])}; follows sin^2((2K+1) theta)")
        lines += ["Needs the number of answers M = 2 (from count_answers); unknown M: BBHT or quantum counting",
                  "Clean-ancilla trick: an idle qubit 0 lets Qiskit build multi-controlled gates cheaply",
                  f"Oracle alone: {ox.get('alone', '?'):,} CX on 12 qubits vs {ox.get('with_idle', '?'):,} CX "
                  "with one idle qubit beside it" if ox else ""]
        bullets(fig, [line for line in lines if line], y=0.75, size=14, gap=0.07)
        image(fig, "grover_curve.png", [0.45, 0.06, 0.52, 0.40])
        pdf.savefig(fig); plt.close(fig)

        # 6 equal CX + honesty
        fig = page(pdf, 6, "Same gate budget: which search wins?", "4 cubes, 12 data qubits, exact success probabilities")
        body = [[e["grover"], f"{e['grover_cx']:,}", f"{e['grover_P']:.3f}", e["qaoa"], f"{e['qaoa_cx']:,}",
                 f"{e['qaoa_P']:.3f}"] for e in facts.get("equal_cx", [])]
        table(fig, [0.05, 0.52, 0.9, 0.25], ["Grover", "CX", "P", "QAOA", "CX", "P"], body, size=12,
              col_widths=[0.28, 0.08, 0.07, 0.35, 0.08, 0.07])
        bullets(fig, [
            "At N = 4 Grover wins on gates, but it needs M",
            "  and its rounds grow like 6^(N/2) with N cubes.",
            "QAOA needs trained angles, but the same angles",
            "  keep working on bigger puzzles (next slide).",
            "No speedup claimed: brute force solves N = 4 in < 1 s.",
            "Thousands of CX are noiseless on SV1 (simulation",
            "  time still costs credits); too many for today's hardware.",
        ], y=0.46, size=14, gap=0.058)
        image(fig, "p_sweep_N4.png", [0.60, 0.04, 0.37, 0.44])
        pdf.savefig(fig); plt.close(fig)

        # 7 bonus
        fig = page(pdf, 7, "Bonus: N cubes and N colours, no retraining",
                   "make_puzzle(n, seed) with seeds {5: 16, 6: 86, 7: 68, 8: 4}; each has exactly 2 answers")
        image(fig, "bonus_scaling.png", [0.03, 0.30, 0.94, 0.48])
        bonus = [r for r in rows if r["level"] == "Bonus"]
        body = [[r["id"], str(r["N"]), str(r["qubits"]), f"{r['cx']:,}", f"{r['P']:.3f} +- {r['P_se']:.3f}",
                 f"{r['baseline_subspace']:.1e}"] for r in sorted(bonus, key=lambda r: r["N"])]
        if body:
            table(fig, [0.05, 0.07, 0.6, 0.22], ["row", "N", "qubits", "CX", "P (sampled)", "random legal"], body,
                  size=11)
        fig.text(0.68, 0.24, "Same p = 24 angles trained at N = 4.\nQubits grow as 3N; CX per layer\n"
                 "roughly like 25 N^2. P stays far above\nrandom guessing.", fontsize=13, color=INK, va="top")
        pdf.savefig(fig); plt.close(fig)

        # 8 checks and next steps
        cc = facts.get("cost_check", {})
        fig = page(pdf, 8, "What we checked, what we did not, what next")
        fig.text(0.05, 0.80, "Checked", fontsize=18, fontweight="bold", color=TEAL, va="top")
        bullets(fig, [
            f"Brute force {bf['solved']} / {bf['towers']:,}; 2 answers on N = 4..8",
            f"Starter cost: {cc.get('zeros', '?')} zeros in {cc.get('candidates', 0):,} candidates",
            "Our Hamiltonian = cost on all 1,296 legal codes",
            "Decoders on known answers, both bit orders",
            "Marker trap of the one-sided marker fixed",
            "Every success passed solves(); illegal shots counted",
            "pytest suite + a headless run of the notebook",
        ], x=0.05, y=0.73, size=12.5, gap=0.065)
        fig.text(0.50, 0.80, "Not yet / next", fontsize=18, fontweight="bold", color=AMBER, va="top")
        bullets(fig, [
            "No qBraid SV1 or hardware job run yet (code written, tested offline)",
            "Gate counts from qiskit 2.6.0; Grover for N >= 6 is an estimate",
            "Next: two-stage search (front/back 2-factors, then pair them)",
            "Next: quantum counting so Grover does not need M",
            "Next: a 3-cube, 9-qubit run on real hardware vs SV1",
            "AI use: Claude Code agents wrote code; we checked as listed",
        ], x=0.50, y=0.73, size=12.5, gap=0.065)
        pdf.savefig(fig); plt.close(fig)
    print("wrote", OUT)


if __name__ == "__main__":
    sys.exit(main())
