# Assets for the deck (owned by the VISUALS agent)

All files live in `presentation/assets/`. PNGs are 2x (200 dpi) on white unless noted; SVGs are the same drawings in vector form.
Palette: navy #1f3b73, blue #1f77b4, red #c0392b, green #2e8b57, amber #b7791f; puzzle colours R #d64541, G #2e9e5b, B #2f74c0, Y #f2c230.

| File | What it shows | Suggested slide | Size |
|---|---|---|---|
| hero_ai_tower_wide.png / .jpg | DECORATIVE AI image: flat four-cube tower on the right, faint circuit lines, empty left side for the title. No data in it. Credit: "Illustration generated with Google Gemini 3 Pro Image (Nano Banana Pro)". | Title slide (full-bleed background, title text on the left) | 2752x1536 (png 2.7 MB, jpg lighter) |
| hero_ai_tower_crop.png / .jpg | Same AI image cropped to the tower only (portrait). Same credit line. | Title slide side image, or closing slide | 1376x1536 |
| tower_solved.png / .svg | The verified solved tower (all_solutions(CUBES)[0], checked with solves): isometric view from front-right and back-left with colour letters, plus a Front/Right/Back/Left grid with a green check under each side. Cube 1 drawn on top. | Problem / "what a solution looks like", or Results | 2069x1173 |
| tower_iso_front.png / .svg | Programmatic hero alternative: the same verified tower, front-right view only, accurate colours. | Title slide (accurate alternative to the AI image) | 693x1076 |
| graph_two_factors.png / .svg | Puzzle as a graph: 4 colour nodes, 12 lines (one per opposite-face pair, coloured by cube), then the front/back pick and the left/right pick of the solution highlighted with cube numbers. | "The puzzle as a graph" / encoding intuition | 2524x1237 |
| chart_p_vs_cx.png / .svg | P(correct tower) vs two-qubit gates at N = 4: QAOA p = 1..24 (blue) and Grover K = 1..19 (red). Every point was built with the repo code, wrapped with runtime.prepare_safe (seed 7) and its CX read with runtime.circuit_metrics; P is exact (Reduced simulator for QAOA; sin^2((2K+1)theta) for Grover, matching exact_distribution to 6e-14 at K = 1, 5, 10, 19). Big markers: measured 4,000-shot rows C0-C2, G0-G2 with 2 SE bars. Dashed random legal guess 0.15 %. | Results (headline chart) | 2082x1217 |
| chart_p_vs_cx_data.json | The measured table behind chart_p_vs_cx (p or K, cx, depth, qubits, P_exact, plus provenance). | data, not for a slide | small |
| chart_bonus_scaling.png / .svg | Bonus N = 4..8, three small panels: qubits (14..26), CX (8.6k..38.8k), P(correct tower) with transferred p = 24 angles (98.4, 48, 36, 16, 28 %); footer with random-guess odds and seeds. | Bonus / scaling | 2738x1099 |
| encoding_compact.png / .svg | Encoding: cube 1's three opposite-face pairs, the table of its 6 legal choices (code 0..5, 3-qubit binary, front/back chip, left/right chip; codes 6, 7 never prepared), and a brick bar of 12 qubits (ours) vs 24 (starter one-hot), plus search-space sizes. | Encoding & approach | 2540x1230 |
| circuits_at_a_glance.png / .svg | Two block diagrams: QAOA (U6 prep per cube, cost layer e^{-i gamma H} with 148 Pauli terms, per-cube mixer, repeat p = 24, P = 98.4 %, 8,648 CX) and Grover (U6 prep, rules-only oracle, diffuser, repeat K = 19, P = 99.8 %, 3,987 CX) with the spare q0 clean-ancilla callout (oracle 880 to 117 CX, 209 CX per iteration, measured as CX(K=19) minus CX(K=18)). | Circuits / method | 2789x1831 |

Notes
- Every number in the programmatic figures is read from `results/results.json`, `results/facts.json`, `results/heavy_rows.json` or computed from `src/puzzle.py` (no fitted values: chart CX counts are transpiled per point by `measure_cx.py`, and the chart script asserts they equal the results.json rows). Scripts: `Resources/scratch/visuals/` (not pushed).
- AI images are decorative only; credit line: "Title illustration generated with Google Gemini 3 Pro Image (Nano Banana Pro); all charts and diagrams drawn from our data."
- wheresryan22/anatomy (MIT) was reviewed: it is a Claude skill plus a Node isometric SVG/WebGL kit for interactive "machine" figures. No Node on this machine and its style targets interactive web figures, so no code or assets were copied; only its general shading idea (lighter tops, darker side faces, thin outlines) informed the isometric tower.
