"""Drawing and bookkeeping helpers for starter_notebook.ipynb and resource 03.

Nothing here is part of the puzzle or the quantum algorithm. The notebooks keep
that code in their own cells, where you can read and change it.
The starter imports `resources.helpers`; notebooks inside resources/ import `helpers`.
"""
import io

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from IPython.display import Image, display
from matplotlib.patches import Rectangle
from qiskit import QuantumCircuit, transpile

SEED = 7
GREY, VIOLET, TEAL, AMBER = "#8A8A8A", "#8B5CF6", "#0E9488", "#C2772A"
PAINT = {"R": "#D64545", "G": "#2FA95F", "B": "#3B82F6", "Y": "#E8B400"}
CUBE_INK = [VIOLET, TEAL, AMBER, "#DB4B92"]

plt.rcParams.update({"figure.facecolor": "none", "axes.facecolor": "none",
                     "savefig.facecolor": "none", "savefig.edgecolor": "none",
                     "figure.dpi": 110, "axes.edgecolor": GREY,
                     "text.color": GREY, "axes.labelcolor": GREY,
                     "xtick.color": GREY, "ytick.color": GREY})

# Pass as circuit.draw("mpl", style=CIRCUIT) to draw on a transparent background.
CIRCUIT = {"backgroundcolor": "#00000000", "linecolor": GREY,
           "textcolor": GREY, "subtextcolor": GREY, "gatetextcolor": "#FFFFFF",
           "displaycolor": {"h": (VIOLET, "#FFFFFF"), "x": (TEAL, "#FFFFFF"),
                            "ry": (VIOLET, "#FFFFFF"), "rx": (TEAL, "#FFFFFF"),
                            "rz": (AMBER, "#FFFFFF"), "rzz": (AMBER, "#FFFFFF"),
                            "cx": (TEAL, "#FFFFFF"), "cz": (AMBER, "#FFFFFF")}}


def show(fig):
    """Show a figure on a transparent background, so it reads in light and dark themes."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", transparent=True, bbox_inches="tight", dpi=110)
    plt.close(fig)
    display(Image(data=buffer.getvalue()))


# ---------------------------------------------------------------- cubes and towers

NET = [[(1, 1), (3, 1)], [(0, 1), (2, 1)], [(1, 2), (1, 0)]]  # (column, row) of each pair's faces


def _face(ax, x, y, colour, size=1.0):
    if colour is None:
        ax.add_patch(Rectangle((x, y), size, size, facecolor="none",
                               edgecolor=GREY, linestyle="--"))
        ax.text(x + size / 2, y + size / 2, "?", ha="center", va="center", color=GREY)
        return
    ax.add_patch(Rectangle((x, y), size, size, facecolor=PAINT[colour],
                           edgecolor="white", linewidth=2))
    ax.text(x + size / 2, y + size / 2, colour, ha="center", va="center",
            color="white", fontsize=11, fontweight="bold")


def _clean(ax, xlim, ylim):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_nets(cubes, title="The four cubes, unfolded"):
    """Draw each cube as a flat cross of six faces."""
    fig, axes = plt.subplots(1, len(cubes), figsize=(2.6 * len(cubes), 2.4))
    for i, (ax, cube) in enumerate(zip(axes, cubes)):
        for pair, places in zip(cube, NET):
            for colour, (x, y) in zip(pair, places):
                _face(ax, x, y, colour)
        _clean(ax, (-0.1, 4.1), (-0.1, 3.1))
        ax.set_title(f"cube {i + 1}", fontsize=10)
    fig.suptitle(title, fontsize=11, color=GREY)
    show(fig)


def draw_tower(tower):
    """Draw a tower of (front, right, back, left) colours, top cube first. None draws a "?"."""
    fig, ax = plt.subplots(figsize=(4.4, 0.95 * len(tower) + 0.6))
    for row, view in enumerate(reversed(tower)):
        for col, colour in enumerate(view):
            _face(ax, col * 1.15, row, colour, size=0.95)
    for col, name in enumerate(["front", "right", "back", "left"]):
        ax.text(col * 1.15 + 0.47, len(tower) + 0.1, name, ha="center", fontsize=9)
    _clean(ax, (-0.1, 4.6), (-0.1, len(tower) + 0.5))
    show(fig)


# ---------------------------------------------------------------- the graph view

DOT = {"R": (0, 1), "G": (1, 1), "B": (1, 0), "Y": (0, 0)}


def draw_graph(cubes, chosen=None, title=""):
    """One dot per colour and one line per opposite pair, coloured by cube.

    chosen[c] is the pair of cube c to draw bold; the other lines turn faint.
    """
    fig, ax = plt.subplots(figsize=(3.6, 3.6))
    seen = {}
    for c, cube in enumerate(cubes):
        for p, (u, v) in enumerate(cube):
            key = tuple(sorted((u, v)))
            n = seen.get(key, 0)
            seen[key] = n + 1
            on = chosen is None or chosen[c] == p
            ax.annotate("", xy=DOT[v], xytext=DOT[u],
                        arrowprops=dict(arrowstyle="-", lw=2.6 if on else 1.0,
                                        color=CUBE_INK[c], alpha=1.0 if on else 0.18,
                                        connectionstyle=f"arc3,rad={0.18 * n * (-1) ** n}"))
    for colour, (x, y) in DOT.items():
        ax.scatter([x], [y], s=620, color=PAINT[colour], zorder=3, edgecolor="white")
        ax.text(x, y, colour, ha="center", va="center", color="white",
                fontweight="bold", zorder=4)
    for c in range(len(cubes)):
        ax.plot([], [], color=CUBE_INK[c], lw=2.6, label=f"cube {c + 1}")
    ax.legend(loc="center left", bbox_to_anchor=(1.0, 0.5), frameon=False, fontsize=9)
    _clean(ax, (-0.35, 1.35), (-0.35, 1.35))
    ax.set_title(title, fontsize=10)
    show(fig)


def orient(cubes, picks):
    """Walk the cycles of a 2-factor. Return {cube: (one side, opposite side)}."""
    lines = {c: cubes[c][p] for c, p in enumerate(picks)}
    placed = {}
    while len(placed) < len(lines):
        c = next(c for c in lines if c not in placed)
        here = lines[c][0]
        while c is not None:
            u, v = lines[c]
            placed[c] = (here, v if u == here else u)
            here = placed[c][1]
            c = next((d for d, (a, b) in lines.items()
                      if d not in placed and here in (a, b)), None)
    return placed


def tower_from(cubes, choice):
    """Turn one (front/back pair, left/right pair) choice per cube into a tower."""
    front = orient(cubes, [fb for fb, _ in choice])
    side = orient(cubes, [lr for _, lr in choice])
    return [(front[c][0], side[c][0], front[c][1], side[c][1]) for c in range(len(cubes))]


# ---------------------------------------------------------------- bitstrings and plots

def solution_strings(picks_list):
    """Bitstrings, in Qiskit order, of front/back picks on the 3-qubits-per-cube layout."""
    out = []
    for picks in picks_list:
        bits = ["0"] * (3 * len(picks))
        for c, p in enumerate(picks):
            bits[3 * c + p] = "1"
        out.append("".join(reversed(bits)))
    return out


def diagonal(H):
    """The value of a Z-only Hamiltonian on every bitstring, indexed like Statevector.probabilities()."""
    idx = np.arange(2 ** H.num_qubits)
    values = np.zeros(len(idx))
    for label, coeff in zip(H.paulis.to_labels(), H.coeffs):
        sign = np.ones(len(idx))
        for q, op in enumerate(reversed(label)):
            if op == "Z":
                sign *= 1 - 2 * ((idx >> q) & 1)
        values += coeff.real * sign
    return values


def plot_cost_counts(scores):
    """Bar chart of how many candidates land on each cost, zero in amber."""
    values, counts = np.unique(scores, return_counts=True)
    fig, ax = plt.subplots(figsize=(7.0, 2.9))
    ax.bar(values, counts, color=[AMBER if v == 0 else VIOLET for v in values], width=0.8)
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.8)
    ax.set_xlabel("cost")
    ax.set_ylabel("candidates (log scale)")
    ax.set_title("Cost of every one-pair-per-axis candidate", fontsize=10)
    show(fig)


def plot_landscape(avg, gammas, betas, best):
    """Heatmap of the average cost over (gamma, beta), with the best angles marked."""
    fig, ax = plt.subplots(figsize=(5.2, 3.9))
    im = ax.imshow(avg, origin="lower", aspect="auto", cmap="viridis",
                   extent=[betas[0], betas[-1], gammas[0], gammas[-1]])
    ax.scatter([best[1]], [best[0]], color=AMBER, s=60, marker="x")
    ax.set_xlabel("mixer angle β")
    ax.set_ylabel("cost angle γ")
    ax.set_title("Average cost, constrained QAOA, p = 1", fontsize=10)
    fig.colorbar(im, ax=ax, label="average cost")
    show(fig)


def plot_history(history, title, ylabel="average cost", target=None):
    """Line plot of the cost at each optimizer step; `target` draws a dashed "best possible" line."""
    fig, ax = plt.subplots(figsize=(6.0, 2.8))
    ax.plot(history, color=VIOLET)
    if target is not None:
        ax.axhline(target, color=TEAL, ls="--", lw=1)
        ax.text(len(history) * 0.98, target + 0.08, "best possible", color=TEAL,
                fontsize=9, ha="right")
    ax.set_xlabel("optimizer step")
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=10)
    show(fig)


def plot_top_counts(counts, good, top=12):
    """Bar chart of the most frequent bitstrings, the ones in `good` in amber."""
    rows = sorted(counts.items(), key=lambda kv: -kv[1])[:top]
    fig, ax = plt.subplots(figsize=(7.4, 2.9))
    ax.bar(range(len(rows)), [n for _, n in rows],
           color=[AMBER if s in good else VIOLET for s, _ in rows])
    ax.set_xticks(range(len(rows)))
    ax.set_xticklabels([s for s, _ in rows], rotation=60, fontsize=7, family="monospace")
    ax.set_ylabel("shots")
    ax.set_title("Most frequent bitstrings (amber = a good front/back pick)", fontsize=10)
    show(fig)


# ---------------------------------------------------------------- resource 03: MaxCut

def draw_network(graph, pos, title=""):
    """Draw a networkx graph at the given node positions."""
    fig, ax = plt.subplots(figsize=(4.6, 2.6))
    nx.draw_networkx(graph, pos, ax=ax, node_color=[VIOLET] * len(graph),
                     edge_color=GREY, font_color="#FFFFFF", node_size=520)
    ax.set_title(title, fontsize=10)
    ax.axis("off")
    show(fig)


def plot_energy_grid(grid, gammas, betas, best):
    """Heatmap of grid[i][j] = <H> at (gammas[i], betas[j]); `best` = (i, j) gets a dot."""
    fig, ax = plt.subplots(figsize=(5.4, 3.4))
    image = ax.imshow(grid.T, origin="lower", aspect="auto", cmap="magma",
                      extent=[gammas[0], gammas[-1], betas[0], betas[-1]])
    ax.plot(gammas[best[0]], betas[best[1]], "o", color=TEAL, ms=8)
    ax.set_xlabel("gamma (cost angle)")
    ax.set_ylabel("beta (mixer angle)")
    ax.set_title("Expected energy for one QAOA round", fontsize=10)
    fig.colorbar(image, ax=ax, label="<H>")
    show(fig)


def plot_top_splits(counts, good, title, top=8):
    """Fraction of shots for the most common bitstrings; the ones in `good` in teal."""
    shots = sum(counts.values())
    keys = sorted(counts, key=counts.get, reverse=True)[:top]
    fig, ax = plt.subplots(figsize=(6.2, 2.8))
    ax.bar(keys, [counts[k] / shots for k in keys],
           color=[TEAL if k in good else GREY for k in keys], width=0.6)
    ax.set_ylabel("fraction of shots")
    ax.set_title(title, fontsize=10)
    ax.tick_params(axis="x", labelrotation=45)
    show(fig)


def draw_cut(graph, pos, teams):
    """Draw a split twice: in the graph's layout, and one column per team. Return (cut, kept) edges."""
    colors = [VIOLET if b == 0 else AMBER for b in teams]
    cut = [(i, j) for i, j in graph.edges if teams[i] != teams[j]]
    kept = [(i, j) for i, j in graph.edges if teams[i] == teams[j]]
    columns = {}
    for side in (0, 1):
        members = [n for n in range(len(teams)) if teams[n] == side]
        for row, n in enumerate(members):
            columns[n] = (side, (len(members) - 1) / 2 - row)

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 2.9))
    for ax, layout, title in [(axes[0], pos, "The graph"),
                              (axes[1], columns, "One column per team")]:
        bend = "arc3,rad=0.45" if layout is columns else "arc3"
        nx.draw_networkx_edges(graph, layout, edgelist=cut, ax=ax, edge_color=TEAL, width=2.6)
        nx.draw_networkx_edges(graph, layout, edgelist=kept, ax=ax, edge_color=GREY, width=1.4,
                               style="dashed", arrows=True, arrowstyle="-",
                               connectionstyle=bend)
        nx.draw_networkx_nodes(graph, layout, ax=ax, node_color=colors, node_size=520)
        nx.draw_networkx_labels(graph, layout, ax=ax, font_color="#FFFFFF")
        ax.set_title(title, fontsize=10, color=GREY)
        ax.axis("off")
    axes[1].axvline(0.5, color=GREY, ls="--", lw=1)
    axes[1].text(0.5, axes[1].get_ylim()[0], "the cut", color=GREY, ha="center",
                 va="top", fontsize=9)
    axes[1].set_xlim(-0.6, 1.6)
    show(fig)
    return cut, kept


# ---------------------------------------------------------------- jobs

def prepare(circuit):
    """Add a marker qubit fixed at 1, measure every qubit, and transpile to basic gates.

    Providers do not all list bits in the same order. The marker is the last
    qubit, so its position in each result shows which end holds the last qubit.
    """
    n = circuit.num_qubits
    qc = QuantumCircuit(n + 1)
    qc.compose(circuit, range(n), inplace=True)
    qc.x(n)
    qc.measure_all()
    return transpile(qc, basis_gates=["rz", "sx", "x", "cx"], optimization_level=1)


def strip_marker(raw):
    """Drop the marker bit and return the counts in Qiskit order (last qubit first)."""
    if all(key[0] == "1" for key in raw):
        return {key[1:]: n for key, n in raw.items()}
    if all(key[-1] == "1" for key in raw):
        return {key[:-1][::-1]: n for key, n in raw.items()}
    raise ValueError("marker bit not found; was the circuit built with prepare?")
