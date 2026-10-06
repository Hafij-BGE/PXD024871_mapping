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

**Status:** RESOLVED as an analysis, but **its inputs are now known to be
wrong in shape.** run-003 verified the real run distribution: 29 units at 3
runs, 17 at 5, a tail at 8/9/10/15. This run assumed 8 at 4 and 6 at 5. Same
222 runs over 52 units, materially different unbalance. The findings that do
not depend on the distribution (B irrelevance, the unfalsifiability of §25,
the metric bias at extreme ratio) stand; the precision and coverage figures
must be recomputed. **Re-run required before the preregistration freeze.**

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

---

## run-003 — Phase A mapping, M1 to M4

| Element | Value |
|---|---|
| Timestamp | 2026-10-06, UTC |
| Stage | S1–S5; gates G1, G2, G3 |
| Purpose | Execute the provenance mapping against the retrieved sources and settle the counts every `[provisional]` figure rested on |
| Serves | `SECTIONS.md` §5A1–§5A3; D001, D005, D011, D012, D013, D021 |
| Code | `scripts/phase_a_mapping.py`, blob `b54d3216a0d44871059270ace089fdb8fe796ff7`; vocabulary `vocab/enrichment_class.tsv` |
| Environment | env-001 |
| Inputs | `data/raw/S1/files_v3_page0..5.json` (504 records), `data/raw/S2/PXD024871_community_annotated.sdrf.tsv` (402 rows); checksums in `data/raw/*/provenance.jsonl` |
| Parameters | Exact normalized matching only (D016); two-field allele pattern; expected complement 6 loci |
| Outputs | `data/derived/FILE_MAP.csv` (402), `FILE_MAP_REJECTS.csv` (0), `ELIGIBILITY.csv`, `UNITS.csv` (52), `UNIT_GENOTYPE.csv`, `ALLELE_FREQUENCY.csv` (46); `results/qc/QC_G1.md`–`QC_G3.md` |
| Software versions | Python 3.11.15, stdlib only |
| Random seed | n/a — deterministic |
| CPU/RAM/GPU | 4 cores, 15 GiB, no GPU |
| Runtime | <2 s |
| Errors/warnings | None. Two G3 checks record FAIL by design; see interpretation |
| Metrics | G1 pass; G2 pass; G3 two FAILs |

### Research record

**Purpose.** Replace every count in the repository that came from description
rather than measurement, and settle the five decisions blocked on retrieval.

**Reasoning.** The network policy was opened, so the sources became reachable.
M1–M4 need only the manifest and the metadata file, so all of G1 and G2 and most
of G3 were executable at once. M5 needs the containers and was not run.

**Alternatives considered.** (a) Explore interactively and report numbers in
conversation — rejected: the governing prompt requires outputs with generating
code, and terminal output is not an artifact. (b) Wait and run M1–M5 together
after retrieving containers — rejected: these gates gate the container
retrieval, and running them first is what surfaced the instrument confound
before any bulk transfer was spent. (c) Substring-match the enrichment
annotation rather than use a term table — rejected by M3's own specification.

**Interpretation.** Below.

**Limitations.** M5 not run; container fan-out unverified. Everything here
asserts only what the deposited annotation asserts (`METHODOLOGY.md` limitation
9), and the metadata file is the one input with no publisher checksum.

**Decision.** D001, D005, D011, D012, D013 resolved; D021 opened and resolved.

**Next step.** Stream S3, then M5 and M6. Re-run run-001 on the observed run
distribution.

### Interpretation

**G1 and G2 pass cleanly.** M1 is an exact 1:1 over 402 acquisitions with zero
rejects in either direction. The class vocabulary has exactly two terms, and the
independent check held: `characteristics[mhc protein complex]` agrees with the
antibody annotation on 402/402 rows, zero conflicts. Genotype parsing produced
zero nomenclature failures across all 52 typed units.

**The consequential finding is a G3 FAIL that cannot be fixed.** Instrument is
*completely* confounded with unit — 25/27, zero overlap, no unit spanning both
platforms. `METHODOLOGY.md` had listed this as a conditional ("if platform
correlates with participant"); it does, totally. §25 cannot be rescued by any
split over units, and no covariate is available to adjust for it, because age
and sex are absent and disease and tissue are uniform. Accepted as a limitation
under D005.

**Two numbers I had wrong.** Containers total 107.53 GiB, not the ~47.8 GB
carried as provisional; peak extraction disk is ~12 GiB, not the ~2 GB I wrote
into the §14 budget table, because the largest container is 9.25 GiB. Corrected
under D021.

**run-001 must be re-run.** Its reconstructed run distribution matched the real
total and range but not the shape — it assumed 8 units at 4 runs and 6 at 5,
against the real 2 and 17. Same 222 runs over 52 units, materially different
unbalance, so the cluster-bootstrap precision figures need recomputing on the
observed distribution.

**Status:** RESOLVED. G1 and G2 pass. G3 passes except M5 (not run) and the
accepted D005 limitation.

---

## run-004 / run-005 — S3 pilot and redundancy measurement

| Element | Value |
|---|---|
| Timestamp | 2026-10-06, UTC |
| Stage | S7 pilot; informs G4. Not a gate pass |
| Purpose | Validate the stream-extract-delete cycle, then measure yield and cross-unit redundancy so §14 could be resized from data |
| Serves | `SECTIONS.md` §14; D004, D007, D021, D022, D023 |
| Code | `scripts/extract_peptides.py` blob `0c984da3c722c3aafbff2cb46d80346fcc546481`; `scripts/reconcile_provenance.py` blob `79f852122607e973311dd326485c6521f1ce8a4a` |
| Environment | env-001 |
| Inputs | 4 class-I containers (UPN03, UPN11, UPN15, UPN25), publisher SHA-1 verified for each; 1.58 GiB transferred |
| Parameters | length window 8–12; unique sequences per unit; pairwise Jaccard |
| Outputs | `data/derived/peptides/{UPN03,UPN11,UPN15,UPN25}.csv` + `.meta.json`; `results/qc/QC_G3_pilot.md` |
| Software versions | Python 3.11.15, stdlib only |
| Random seed | n/a |
| CPU/RAM/GPU | 4 cores, 15 GiB, no GPU |
| Runtime | ~25 min, transfer-dominated (~1.5 MiB/s) |
| Errors/warnings | One transfer truncated at 77.4% and left unrecorded; caught by reconciliation, re-fetched clean. See D023 |
| Metrics | 49,373 / 51,219 / 45,057 / 41,578 unique per unit; pairwise overlap 2.9–6.2%; Heaps' β 0.923 |

### Research record

**Purpose.** Resize §14 from measurement, as the author directed, rather than
proceed with a budget known to be wrong.

**Reasoning.** Union size is a between-unit property, so one unit could not give
it. Four units give six pairs, enough for a redundancy estimate and a Heaps' fit,
at ~1.6 GiB rather than 47.85 GiB.

**Alternatives considered.** (a) Size for the no-redundancy worst case, 3.65M —
rejected as needlessly conservative when redundancy is cheap to measure.
(b) Download all 52 first and size afterwards — rejected; that is the 9-hour
transfer the resize was supposed to inform. (c) Assume literature redundancy
figures — rejected; no source was available to cite and the measurement cost
little.

**Interpretation.** Below.

**Limitations.** Four units of 52; β weakly determined. The four were chosen as
the smallest containers, which turned out to make five of six pairs
genotype-disjoint — a selection effect on the quantity being estimated, and the
reason the projection is stated as an order of magnitude.

**Decision.** D022, D023 resolved; D004 and D007 reframed; D021 corrected.

**Next step.** Settle the hardware question before the freeze. Extract more
shared-allele pairs to firm the projection.

### Interpretation

**The cycle works, and the pilot earned its place by failing two checks.** M5's
specified join path does not work for this submission (QC_G3_pilot), and one
transfer truncated silently (D023). Both were found at 1.6 GiB instead of 47.85.

**Yield is 411× the run-001 assumption** and redundancy is low: 2.9–6.2%
pairwise, with the fourth unit still 92% novel. The union projects to ~1.9M,
against the 100,000 §14 was sized for.

**D007 clears by a wide margin.** **D004 is nearly a no-op** at the
unique-sequence level — the confidence filter removes 0.5% — so purity control
must come from the score table instead.

**D003's premise was wrong in the reassuring direction.** I argued that
ligandomes overlap heavily between units sharing alleles, making cross-split
leakage a serious concern. Measured overlap is 3–6%, and the single
shared-allele pair sits inside the genotype-disjoint range. The leakage risk is
much smaller than I claimed, though one pair is thin evidence.

**Status:** RESOLVED as a pilot. G4 not attempted: 48 of 52 containers remain.
