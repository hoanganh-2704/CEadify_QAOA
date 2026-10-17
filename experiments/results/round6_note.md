# Round 6 note: depth sweep p = 1 to 10 (N = 4)

1. The only change is that I kept the angles at every depth on the way up instead of only the last one. To do that I split the layer loop into `train_layers`, which makes the same optimizer calls and returns each p's angles. The recipe is the accepted one: per-pair reduced Hamiltonian, full XY mixer, Gibbs eta = 1, layer-by-layer COBYLA from the p=1 grid point with N(0, 0.05) jitter, seeds 0, 1 and 2, and the same maxiter rule, now run up to p = 10.
2. The check is right because a sweep reports 30 numbers. If any (seed, p) value did not come from its own saved angles, the curve could be wrong without anyone noticing. So the test recomputes every P(solved) from that p's stored angles, rebuilds each per-p median/min/max from those runs, and recomputes the p=7 drift against round4.json without requiring it to be zero.
3. I wrote `experiments/tests_round6.py` first and ran `.venv\Scripts\python.exe -m pytest experiments/tests_round6.py -q -p no:cacheprovider` (red), then `.venv\Scripts\python.exe experiments/run_round.py 6` (about 45 s per seed up to p = 10), then the round-6 tests and the full suite (green).
4. The numbers:
   - Exact P(solved) climbs from 1.14% at p = 1 to 35.12% at p = 7 and 55.19% at p = 10.
   - Every extra layer costs exactly 274 CX (GRADING call) and adds 118 to 130 to the depth.
   - Each layer bought 1.7, 3.5, 5.7, 8.3, 7.1, 7.7, 6.7, 6.7 and 6.7 points of P(solved) for p = 2 to 10.
   - So in this noiseless simulation no layer up to p = 10 stopped paying for itself. I did not measure noise, which is what would make extra layers stop paying on real hardware.
   - The p = 7 angles match round4.json exactly (drift 0.0 for all three seeds).

Seed spreads are at most 0.04 points at every p. I am not picking a p.

Red pytest line (before implementing, tests_round6.py only):
`4 errors in 3.29s`

Green pytest lines (after implementing):
- `experiments/tests_round6.py`: `4 passed in 2.71s`
- Full suite (`experiments/tests_quantum.py experiments/tests_round2_review.py experiments/tests_round3_review.py experiments/tests_round4.py experiments/tests_round5.py experiments/tests_round6.py tests`): `99 passed in 44.53s`

## Depth table (N = 4, seeds 0–2, exact subspace P(solved); random legal pick 0.154%)

| p | P(solved) median [min, max] | gain vs p-1 (points) | CX (GRADING) | added CX | depth (GRADING) |
|---|---|---|---|---|---|
| 1 | 1.14% [1.14, 1.14] | – | 314 | – | 180 |
| 2 | 2.85% [2.85, 2.86] | +1.71 | 588 | 274 | 297 |
| 3 | 6.34% [6.34, 6.34] | +3.49 | 862 | 274 | 425 |
| 4 | 12.00% [11.97, 12.01] | +5.66 | 1136 | 274 | 551 |
| 5 | 20.29% [20.29, 20.29] | +8.29 | 1410 | 274 | 666 |
| 6 | 27.39% [27.39, 27.39] | +7.10 | 1684 | 274 | 792 |
| 7 | 35.12% [35.11, 35.12] | +7.73 | 1958 | 274 | 920 |
| 8 | 41.83% [41.83, 41.84] | +6.71 | 2232 | 274 | 1038 |
| 9 | 48.52% [48.52, 48.52] | +6.69 | 2506 | 274 | 1168 |
| 10 | 55.19% [55.19, 55.20] | +6.68 | 2780 | 274 | 1286 |

## Course question: why 35% at 4 cubes but 9% at 5?

Going from 4 to 5 cubes multiplies the legal picks by 6 (1,296 to 7,776), but the puzzle still has only 2 answers. So the answers are a 6 times smaller target. A random legal pick drops by the same factor, from 0.154% to 0.0257%. Our circuit fell less than that: it went from about 228 times random to about 363 times random. It still fell by almost 4x, because we gave it the same 7 layers to find a smaller target.

That fits what the course says about NP-hard problems. No quantum method is known to solve them with an exponential speedup in general. The best known general gain for this kind of search is quadratic. So any fixed amount of quantum work should succeed less often as the puzzle grows, and the layers or repetitions you need should keep growing with N. Two sizes cannot show a scaling law, and brute force is still faster here at both sizes, so we claim no speedup.

The depth p works like the total time of a slow anneal from the mixer's easy starting state toward the cost's answer states. An anneal only lands on the answer reliably if it runs slowly compared with how close the competing states get to the answer, and that margin usually shrinks as the problem grows. With p held at 7 for both sizes, the 5-cube run is effectively a faster, rougher anneal, so more of the state is left in near-miss towers. The sweep above shows that even at 4 cubes, p = 10 is still far from the slow limit: P(solved) keeps gaining about 6.7 points per layer.
