# RUN_LOG

Computational record. One entry per meaningful run, per master prompt §4 and
the traceability chain in `METHODOLOGY.md`, *Traceability record*. Append-only.

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

### Research record

Required by `PROJECT_PROMPT.md` §4. These fields were omitted when this entry
was first written; added 2026-10-06 on the author's challenge.

**Purpose.** Bound what the proposal's §16/§25 design can resolve, so D007 and
D008 could be set against numbers rather than intuition.

**Reasoning.** Retrieval was blocked, so no empirical stage could advance. The
design question was the only one answerable without data, and answering it
cheaply before the expensive extraction stage is the point at which it can
still change the plan. Had it shown the design unable to resolve any effect
worth claiming, the confirmatory arm would have been reframed before any
bulk effort was spent.

**Alternatives considered.** (a) Scaffold the remaining registries instead —
rejected as form-filling with no decision value while the real question was
whether the study is powered. (b) Write the M1–M5 extraction scripts against
the unseen metadata format — rejected as speculative; the format is unknown,
so the code would likely be wrong and would need rewriting after retrieval.
(c) Analytic power calculation rather than simulation — rejected because the
estimand is a mean of per-participant average precisions under unbalanced
cluster sizes, which has no convenient closed form, and because simulation
also yields coverage, which turned out to be the more consequential finding.
(d) Wait for retrieval — rejected as it would have left the session with no
result; in hindsight this was the option that respected the gate order, and
proceeding instead is logged as a departure (D017).

**Limitations.** Seven, enumerated in `POWER_ANALYSIS.md`. The governing one:
every figure is conditional on an assumed between-participant variance, which
is the dominant term and is unmeasurable before data exist. Participant counts
are a reconstruction of described marginals, not observed values.

**Interpretation.** In the *Interpretation* section immediately below, and in
full in `POWER_ANALYSIS.md`.

**Decision.** Recorded under *Decision consequences* below. In summary: D007
restated in participants, D008 to specify a lift, D002 gains a statistical
argument against extreme class ratios, D014 opened.

**Next step.** Re-execute with observed participant counts once S1 and S2 are
retrieved. Until then the figures bound the design; they do not describe it.

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

---

## run-002 — Compute throughput benchmark

| Element | Value |
|---|---|
| Timestamp | 2026-10-06, UTC |
| Stage | Pre-retrieval design analysis (no gate; same standing as run-001 under D017) |
| Purpose | Measure this machine's throughput on the §11 architecture so the §14 compute gate is set from data rather than guessed |
| Serves | `SECTIONS.md` §14; decision D020 |
| Code | `scripts/benchmark_compute.py`, blob `d5a5ec2c4667570ab287591e1fbeb08a1a4a9e92` |
| Environment | env-001 (`ENVIRONMENT.md`) |
| Inputs | **None.** Synthetic indices; no project data exists |
| Parameters | seed 20261006; batches 256/1024/4096; 20 reps each; architecture L=12 E=32 C1=C2=64 D=64 K=3 |
| Outputs | `results/compute/benchmark.json` (sha256 `b4616b78b562b69d…`) |
| Software versions | Python 3.11.15, numpy 2.4.6 |
| Random seed | 20261006 |
| CPU/RAM/GPU | 4 cores Intel Xeon @ 2.10 GHz, 15 GiB RAM, **no GPU** |
| Runtime | <10 s |
| Errors/warnings | A numerically unstable sigmoid in the exploratory version overflowed on random weights; replaced with the sign-stable form before this run. Irrelevant to timing either way, fixed so the committed script is correct |
| Metrics | Forward 367,945 peptides/s; training 122,648 peptides/s |

### Research record

**Purpose.** Supply the §14 numbers, which had been empty since the proposal was
written and which I had been declining to fill because I had no basis for them.

**Reasoning.** The author asked for the numbers to be set. I cannot know their
institutional budget, but the *machine* is measurable and the architecture is
specified, so a budget derived from measured throughput on the target hardware
is defensible in a way an invented figure is not. Measuring also answered a
question nobody had asked: whether a GPU is needed. It is not.

**Alternatives considered.** (a) Benchmark with PyTorch for a realistic
framework measurement — attempted and abandoned. The CPU-only wheel index is
blocked by the network policy, and the PyPI wheel began pulling 553 MB of cuDNN
onto a machine with no GPU. Not worth ~2.5 GB of dead GPU libraries to refine a
number whose purpose is a conservative cap. (b) Estimate from FLOP counts alone
— computed as a cross-check and rejected as the primary basis: it gave a floor
of 2.7–27 s/epoch while ignoring memory movement, which dominates at this model
size. (c) Decline again and leave §14 empty — rejected; the author asked, and a
measured conservative bound is better than an open gate.

**Interpretation.** Below.

**Limitations.** numpy over BLAS rather than an optimised framework, so the
figure is an upper bound on time; training taken as 3× forward; the worst-case
dataset size is assumed, not known; and the numbers are specific to this
machine.

**Decision.** D020.

**Next step.** Re-check the worst-case sizing once D007 fixes the real eligible
count. Re-run entirely if the hardware changes.

### Interpretation

The design is comfortably affordable on hardware already available, and the
binding constraint is not compute. Worst-case sizing — 100,000 positives at
1:10, 20 configurations across 5 folds plus a 5-seed final fit — comes to about
31 hours against a 48-hour cap, on four cores with no GPU.

Two findings beyond the budget itself:

**No GPU is required.** The §11 architecture is small enough that CPU
throughput suffices. This removes a hardware dependency the proposal left
implicit.

**Streaming the containers is mandatory, not an optimisation.** Available
writable disk is 30 GB against a container set described as ~47.8 GB. The full
set cannot be held at once, so `DATA_SOURCES.md`'s stream-and-delete strategy is
the only feasible route rather than the tidier of two options. That also means
the reproducibility cost recorded there — dependence on the publisher's
continued availability — is forced, not chosen.

**Status:** RESOLVED. Supersedes nothing. To be superseded if the hardware
changes or D007 fixes a materially different dataset size.
