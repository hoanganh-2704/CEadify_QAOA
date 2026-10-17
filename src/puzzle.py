"""The puzzle itself: starter functions (colour-safe), brute force, the cost table and baselines."""
import itertools
import random

import numpy as np

from resources.helpers import SEED, diagonal, orient, solution_strings, tower_from  # noqa: F401

COLOURS = "RGBY"

CUBES = [
    ["GR", "BR", "GY"],   # cube 1
    ["GY", "RB", "BY"],   # cube 2
    ["BR", "RG", "RY"],   # cube 3
    ["YR", "RG", "BG"],   # cube 4
]

CHOICES = list(itertools.permutations(range(3), 2))  # code k -> (front/back pair, left/right pair)

LAMBDA, MU = 2, 2

# seeds checked to give exactly one tower (2 graph-level answers: the tower and its quarter turn)
BONUS = {5: 16, 6: 86, 7: 68, 8: 4}
SEED3 = 38   # first seed with exactly one tower for N = 3
ALT4 = 57    # a second 4-cube puzzle, used to train angles for the fairness row


def letters_of(cubes):
    """The sorted colour letters that appear on the cubes (what count_answers uses)."""
    return sorted({ch for cube in cubes for pair in cube for ch in pair})


# ---------------------------------------------------------------- starter functions

def orientations(cube):
    """The 24 ways a cube can sit, as (front, back, left, right) colours."""
    views = []
    for a, b in itertools.permutations(range(3), 2):   # front/back pair, left/right pair
        for fa in (0, 1):
            for fb in (0, 1):
                fb_pair, lr_pair = cube[a], cube[b]
                views.append((fb_pair[fa], fb_pair[1 - fa], lr_pair[fb], lr_pair[1 - fb]))
    return views


def solves(tower):
    """True when each of the four sides shows four different colours."""
    return all(len({view[side] for view in tower}) == len(tower) for side in range(4))


def degrees(cubes, picks, colours=None):
    """How many picked lines touch each colour."""
    count = dict.fromkeys(colours or letters_of(cubes), 0)
    for cube, p in zip(cubes, picks):
        for colour in cube[p]:
            if colour in count:
                count[colour] += 1
    return count


def is_two_factor(cubes, picks, colours=None):
    """True when every colour is touched by exactly two picked lines."""
    return all(d == 2 for d in degrees(cubes, picks, colours).values())


def front_back_picks(cubes):
    """Every front/back pick (one pair per cube) that is a 2-factor of the colour graph."""
    return [picks for picks in itertools.product(range(3), repeat=len(cubes))
            if is_two_factor(cubes, picks)]


front_back = front_back_picks(CUBES)


def cost(cubes, x, y, colours=None):
    """x[c][p], y[c][p] are 0/1. Zero exactly for a solved tower."""
    colours = colours or letters_of(cubes)
    total = 0
    for c in range(len(cubes)):
        total += LAMBDA * ((sum(x[c]) - 1) ** 2 + (sum(y[c]) - 1) ** 2)
        total += MU * sum(x[c][p] * y[c][p] for p in range(3))
    for picks in (x, y):
        for k in colours:
            d = sum(cubes[c][p].count(k) * picks[c][p]
                    for c in range(len(cubes)) for p in range(3))
            total += (d - 2) ** 2
    return total


def one_hot(p):
    """The 0/1 row [p == 0, p == 1, p == 2]."""
    return [int(i == p) for i in range(3)]


def make_puzzle(n, seed):
    """N cubes, N colours, a planted answer: two random cycles through all colours."""
    rng = random.Random(seed)
    letters = "".join(chr(ord("A") + i) for i in range(n))
    cycles = []
    for _ in range(2):
        order = rng.sample(letters, n)
        lines = [order[i] + order[(i + 1) % n] for i in range(n)]
        rng.shuffle(lines)
        cycles.append(lines)
    cubes = []
    for i in range(n):
        third = rng.choice(letters) + rng.choice(letters)
        pairs = ["".join(rng.sample(pair, 2)) for pair in (cycles[0][i], cycles[1][i], third)]
        rng.shuffle(pairs)
        cubes.append(pairs)
    return cubes


def count_answers(cubes):
    """How many of the 6**n cases solve the puzzle."""
    letters = sorted({ch for cube in cubes for pair in cube for ch in pair})
    total = 0
    for choice in itertools.product(CHOICES, repeat=len(cubes)):
        for side in (0, 1):
            deg = dict.fromkeys(letters, 0)
            for cube, pick in zip(cubes, choice):
                for ch in cube[pick[side]]:
                    deg[ch] += 1
            if any(d != 2 for d in deg.values()):
                break
        else:
            total += 1
    return total


# ---------------------------------------------------------------- our additions

def instance(n):
    """The puzzle used for n cubes: CUBES for 4, the BONUS seeds for 5..8, SEED3 for 3."""
    if n == 4:
        return CUBES
    if n == 3:
        return make_puzzle(3, SEED3)
    if n in BONUS:
        return make_puzzle(n, BONUS[n])
    raise ValueError(f"no instance chosen for n = {n}")


def brute_force_towers(cubes):
    """Every one of the 24**N orientation towers that solves the puzzle (N <= 5 only)."""
    if len(cubes) > 5:
        raise ValueError("brute force over 24**N towers is limited to N <= 5")
    options = [orientations(cube) for cube in cubes]
    return [tower for tower in itertools.product(*options) if solves(tower)]


def cost_table(cubes):
    """Degree cost sum over both sides and all colours of (deg - 2)**2 for every code tuple.

    Index = sum_c k_c * 6**c (cube 0 is the fastest digit); k_c indexes CHOICES.
    """
    n = len(cubes)
    letters = letters_of(cubes)
    # f[side, cube, code, colour] = how often that colour is on the chosen pair of that side
    f = np.zeros((2, n, 6, len(letters)), dtype=np.int64)
    for c, cube in enumerate(cubes):
        for k, pair_ids in enumerate(CHOICES):
            for side, p in enumerate(pair_ids):
                for ch in cube[p]:
                    f[side, c, k, letters.index(ch)] += 1
    index = np.arange(6 ** n)
    digits = [(index // 6 ** c) % 6 for c in range(n)]
    total = np.zeros(6 ** n, dtype=np.int64)
    for side in range(2):
        deg = np.zeros((6 ** n, len(letters)), dtype=np.int64)
        for c in range(n):
            deg += f[side, c][digits[c]]
        total += ((deg - 2) ** 2).sum(axis=1)
    return total


def verify_choice(cubes, choice):
    """True when the choice builds a solved tower: solves(tower_from(cubes, choice)) and nothing else."""
    return solves(tower_from(cubes, choice))


def all_solutions(cubes):
    """Every (front/back, left/right) choice with cost 0, each one checked with verify_choice."""
    n = len(cubes)
    out = []
    for index in np.flatnonzero(cost_table(cubes) == 0):
        choice = [CHOICES[(int(index) // 6 ** c) % 6] for c in range(n)]
        if not verify_choice(cubes, choice):
            raise AssertionError(f"cost 0 but not a tower: {choice}")
        out.append(choice)
    return out


def baseline(n, kind, m=2):
    """Chance that one uniform random guess is an answer, for the search space named by kind.

    bits3N / bits6N: any bitstring on 3N / 6N qubits; valid6N: one of the 6**N valid codes;
    WxW: one W state per triple (9**N); fb_bits / fb_valid: front/back warm-up, counting the
    front/back 2-factors of instance(n) as the good outcomes (m is not used for these two).
    """
    if kind == "bits3N":
        return m / 2 ** (3 * n)
    if kind == "bits6N":
        return m / 2 ** (6 * n)
    if kind == "valid6N":
        return m / 6 ** n
    if kind == "WxW":
        return m / 9 ** n
    if kind in ("fb_bits", "fb_valid"):
        n_fb = len(front_back_picks(instance(n)))
        return n_fb / (2 ** (3 * n) if kind == "fb_bits" else 3 ** n)
    raise ValueError(f"unknown baseline kind {kind!r}")
