# Round 9 assignment (one change: noise-rate grid for the submitted file)

**Question:** for the exact file sent to IonQ (`results/hardware_n3_p1.qasm`, SHA-256 `a666efe3…ce515e`, 215 CX, with marker), what solved and kept counts should a 100-shot run give if the device's noise is anywhere in a plausible range? At which noise levels would such a run still be distinguishable from the 7.41% post-selected random rate? This is the prediction the hardware row will be compared against. Write it down before the IonQ result exists.

**The one change:** a noise-grid runner that loads the file (checking its hash), simulates it under each grid point, and passes the counts through `results_row(..., marker=True)`. Do not re-transpile, retrain, or edit the file.

**Grid (stated assumptions, not a device spec):**
- cx depolarizing error 0.3%, 0.5% or 1%, crossed with symmetric readout error 0.5% or 2% per qubit (6 points);
- sx/x error 5e-4 and no rz error at every point;
- no routing (the device is all-to-all);
- for each point: Aer, 2000 shots, `seed_simulator = 7`.

**Report (`results/round9.json` and the four-sentence note), for each grid point:**
- all-shot P, the kept (one-hot) fraction, and post-selected P from the 2000 shots;
- scaled to 100 shots: the expected kept and solved counts;
- a 95% interval for solved/kept at 100 shots (binomial, from the simulated rates);
- the one-sided binomial p-value against 7.41% at the expected counts.

Also add one noiseless row. State plainly that IonQ recompiles to native gates, so the grid is a band, not a model of the device.

**Invariant the test checks first:**
1. The simulated circuit is loaded from the file and its SHA-256 matches `round8.json`.
2. With all noise set to zero, the run is within 3σ of the exact P(solved), 100% one-hot, and no marker shots are dropped.
3. Every reported rate and expected count recomputes from the saved counts.
