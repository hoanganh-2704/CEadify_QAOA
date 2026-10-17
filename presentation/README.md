# Presentation (8 slides, 5-minute talk)

`index.html` is a self-contained slide deck (inline CSS and JS, images in `assets/`). It works offline in any
modern browser.

## Open and present

1. Open `presentation/index.html` in Chrome, Firefox or Edge (double-click, or `xdg-open index.html`).
2. Press **F** for full screen.
3. Keys: **Right / Space / Enter / PageDown** next, **Left / PageUp / Backspace** back, **Home / End** first and
   last slide, **N** shows the speaker notes for the current slide, **H** shows the key help.
   Clicking the right 70 % of the screen goes forward, the left 30 % goes back.
4. A slide can be opened directly with `index.html#5`.

Each slide has 2 to 3 sentences of speaker notes (press **N**, or read the `<aside class="notes">` blocks), so any
team member can present it. Suggested timing: 30 / 35 / 35 / 55 / 50 / 35 / 40 / 30 seconds (5 minutes).

## Exported copies

- `export/slides.pdf`: 8 pages, 16:9 (1920 x 1080 px), text selectable.
- `export/slide_1.png` ... `slide_8.png`: 1920 x 1080 screenshots.

They are made with Playwright (headless Chromium) from `index.html`; re-export after any change.

## Sources of the numbers

- Perfect simulator: exact noiseless probabilities (`P_exact` in `results/results.json`, `p_ideal` in
  `results/qpu_counts/*.json`).
- qBraid SV1: computed from `results/sv1_counts/*.json` with the project's own `strip_marker_safe`, `decode_tower`
  and `success_rate`; every success re-checked with `solves`. Job IDs in `results/jobs.json`.
- Rigetti QPU (`rigetti:rigetti:qpu:cepheus-1-108q`): `results/qpu_counts/*.json` and
  `Resources/reviews/qpu_results.md`. Cells still marked "running" had no finished job when the deck was exported.
- Bonus chart, graph and circuit figures: `assets/` (see `assets/MANIFEST.md`); the 25,666 CX "no spare qubit"
  figure is from the notebook's Grover section.

The title-slide illustration is AI-generated (Google Gemini 3 Pro Image) and decorative only; it is credited on
the slide.
