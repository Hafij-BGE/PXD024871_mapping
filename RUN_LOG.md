# RUN_LOG

Computational record. One entry per meaningful run, per master prompt §4 and
the traceability chain in `METHODOLOGY.md` §6. Append-only.

---

## run-001 — Power and resolution analysis

| Element | Value |
|---|---|
| Timestamp | 2026-10-06, UTC |
| Stage | Pre-retrieval design analysis (not a pipeline stage; no gate) |
| Purpose | Bound what the §16/§25 design can resolve, to set D007 and D008 against numbers |
| Serves | `SECTIONS.md` §15, §16, §25; decisions D007, D008 |
| Code | `scripts/power_analysis.py`, blob `891700e696b713e729436ccbcd79336e43af6b6f` |
| Environment | env-001 (`ENVIRONMENT.md`) — Python 3.11.15, numpy 2.4.6, scipy 1.17.1 |
| Inputs | **None.** Simulation only; no project data exists yet |
| Parameters | seed 20261006; n_sim 250 (150 paired); B 2,000; α 0.05; pos/run 40; participant counts reconstructed from described marginals |
| Outputs | `results/power/power_grid.csv` (91 rows, sha256 `80ca965b144f09ad…`)<br/>`results/power/power_params.json` (sha256 `1386d441a6d45765…`) |
| Runtime | ~4 min, 4 cores |
| Errors/warnings | None. A first attempt was abandoned for being ~10× slower than necessary (uncached estimand); no results were produced by it |
| Metrics | CI half-width, nominal-95% coverage, power vs prevalence, paired power |

### Validation performed

Estimators were cross-checked rather than assumed correct:

- Analytic AP at zero discrimination returns prevalence exactly (0.500000,
  0.100000, 0.010000 at the three prevalences tested).
- Analytic AP agrees with the empirical estimator to three decimals
  (0.3592 vs 0.3589 at d=1.190, prevalence 0.1).
- Perfect separation gives AP 1.0; random scores give AP ≈ prevalence (0.1058
  against 0.10 over 400 replicates).
- The asymptotic integral is insensitive to grid resolution: identical to four
  decimals between 8001 and 24001 points.

### Interpretation

Written up in `POWER_ANALYSIS.md`. Seven findings; the consequential ones:
the §25 hypothesis as worded is nearly unfalsifiable (power 1.00 even at AUROC
0.60); resolution is set by held-out participant count and not by B, which is
irrelevant across a 250-fold range; nominal 95% intervals deliver 0.66–0.95
actual coverage; at 1:100 the AP estimator is upward-biased by ~10% of the
lift, and that bias rather than interval width drives the worst miscoverage.

### Decision consequences

- D007 should be restated in **participants**, not peptides.
- D008 should specify a **lift** over prevalence, not a direction.
- D002 gains a statistical argument against extreme class ratios.
- **D014 opened**: whether §18's paired comparison should become the primary
  endpoint, since it is better powered at every participant count tested.

### Supersession

Every figure is conditional on an assumed between-participant variance and on
reconstructed participant counts. This run must be **re-executed with observed
counts** once S1/S2 are retrieved. Until then its numbers bound the design;
they do not describe it.

**Status:** RESOLVED as an analysis. Supersedes nothing. To be superseded by
run-00N after retrieval.
