# PXD024871 CNN Experiment — Sections with Status

## Section Tracking Template

Each section of the experiment has:
- **Purpose**: Research question and goal
- **Why the method is needed**: Justification for this approach over the alternatives
- **Input & Sources**: Data needed
- **Methodology**: How it will be done
- **Metrics & QC**: Validation criteria
- **Expected Outcome**: What we're looking for
- **Limitations**: Known constraints
- **Status**: OPEN / IN_PROGRESS / RESOLVED / PERMANENT
- **Next Step**: What unblocks progression

---

## § 1. Purpose & Research Questions

**Purpose:** Define standalone CNN experiment to test sequence-based learning on PXD024871 HLA-I peptides.

**Why this method is needed:** The experiment's scope must be fixed before any data is touched, otherwise the research question drifts to fit whatever the data turns out to support. Freezing it is what makes a later result confirmatory rather than a description of what was found.

**Input & Sources:**
- CNN Experiment Proposal (doc)
- T-A4 project context and existing predictors

**Methodology:**
- Establish primary and secondary research questions
- Clarify relationship to O9 (7,371 potential sequences)
- Document CNN's independence from provenance/file mapping

**Metrics & QC:**
- Questions clearly stated
- Non-claims documented
- Scope boundaries defined

**Expected Outcome:**
- Agreed research questions frozen
- CNN experiment scope isolated from mapping

**Limitations:**
- Secondary questions may broaden during analysis
- CNN performance ceiling depends on upstream data quality

**Status:** OPEN (awaiting Phase A completion)

**Next Step:** Lock questions after Phase A provenance mapping establishes eligible dataset size.

---

## § 5A. Phase A1 — Dataset Inventory

**Purpose:** Obtain and preserve complete PXD024871 file inventory, metadata, and provenance.

**Why this method is needed:** Checksums and a retrieval record are what let any later claim be traced to a specific file state. Without them the whole pipeline rests on files that cannot be shown to be the ones analysed, and the clean-environment reproduction the prompt requires at completion becomes impossible.

**Input & Sources:**
- PRIDE accession PXD024871
- SDRF: PXD024871_community_annotated.sdrf.tsv (402 rows)
- 504 files: 402 RAW, 101 .msf, 1 SDRF
- Checksums (SHA-1 present except SDRF)

**Methodology:**
- Download SDRF and file manifest from PRIDE
- Verify checksums for all files
- Record retrieval date, accession, version
- Preserve raw metadata unmodified

**Metrics & QC:**
- All 504 files inventoried
- Checksums verified where present
- Metadata integrity confirmed

**Expected Outcome:**
- PXD024871_INVENTORY.csv (file listing with hashes)
- PXD024871_SDRF.tsv (preserved metadata)
- PROVENANCE_RECORD.json (retrieval details)

**Limitations:**
- Identification containers total 107.53 GiB over 101 files (verified); largest single container 9.25 GiB, so streaming is required
- SDRF has 402 rows; 504 files include non-MS-run files

**Status:** RESOLVED — executed, G1 passed (run-003)

**Next Step:** Download SDRF, verify file inventory, record metadata.

---

## § 5A2. Phase A2 — File Mapping Table

**Purpose:** Create file-level mapping from raw files to normalized biological units with HLA class and donor context.

**Why this method is needed:** Class and participant cannot be read off filenames without inventing assertions the metadata does not make. An explicit mapping table is the only way each eligibility decision stays auditable to the source cell that produced it.

**Input & Sources:**
- SDRF (402 rows, 1 per MS run)
- characteristics[antibody enrichment] (W6/32 or L243/Tue39)
- characteristics[individual] (donor ID)
- characteristics[biological replicate]
- comment[technical replicate]
- comment[fraction identifier]
- **characteristics[mhc typing]** (4-digit HLA alleles, 52 donors typed)

**Methodology:**
- Parse SDRF into mapping table
- Extract HLA class from antibody enrichment evidence
- **[BLOCKER #1] Add hla_genotype column with 4-digit alleles from mhc typing**
- Normalize unit_id from individual + replicate + fraction
- Map raw_file → sample_id → unit_id

**Metrics & QC:**
- 402 rows mapped (1:1 with SDRF)
- 222 confirmed class-I runs (W6/32 antibody)
- 52 class-I donors with genotypes
- No rows missing HLA context
- Duplicate unit_ids detected and handled

**Expected Outcome:**
- PXD024871_FILE_MAP.csv (raw_file, sample_id, unit_id, hla_class, hla_genotype, …)
- Mapping statistics and QC report
- Unmapped/ambiguous records list

**Limitations:**
- Class assignment depends on SDRF accuracy
- 10 donors partially typed (4–5 alleles instead of 6)
- Some alleles may be hemizygous

**Status:** RESOLVED — D001 resolved; file map built, G2 passed (run-003)

**Next Step:** Resolve DECISION_LOG #1, then execute file map.

---

## § 5A3. Phase A3 — Biological Unit Resolution

**Purpose:** Normalize files to independent biological units (donors) for later model splitting.

**Why this method is needed:** Files are not participants. Splitting or counting before units are resolved would treat replicates as independent observations, inflating apparent sample size and narrowing every uncertainty interval around a statistic whose real resolution is set by participant count.

**Input & Sources:**
- PXD024871_FILE_MAP.csv (from A2)
- unit_id assignments

**Methodology:**
- Group files by unit_id
- Count runs, replicates, fractions per unit
- Verify 1:1 or 1:N structure is consistent
- Document any replicates with conflicting metadata

**Metrics & QC:**
- All 402 runs assigned to units
- Unit counts match metadata
- Conflicts logged and resolved
- Donor count = 52 confirmed

**Expected Outcome:**
- PXD024871_UNITS.csv (unit_id, donor_id, run_count, hla_genotype, …)
- Unit-level summary

**Limitations:**
- Cannot separate donors with identical allotype + metadata

**Status:** RESOLVED — 52 class-I units resolved, G3 passed (run-003)

**Next Step:** Execute after A2 complete.

---

## § 6. Phase B — Dataset Definition

**Purpose:** Define positive and negative example sets with quality filtering frozen before CNN training.

**Why this method is needed:** Filtering rules chosen after seeing model performance are not rules, they are tuning. Freezing them first is what separates a preregistered result from a selected one.

**Input & Sources:**
- 222 class-I MS runs (eligible set)
- Peptide identifications from .msf files
- Proteome Discoverer percolator q-values (≤ 0.05, default; may be re-filtered)

**Methodology:**
- Stream .msf files, extract peptide tables
- Apply predefined filtering: length 8–12, q ≤ 0.05 (or stricter)
- **[BLOCKER #2] Select negative-control strategy (A: reference-derived, B: decoy, C: hard negatives)**
- Generate negatives matching positive properties
- Remove exact duplicates across splits
- Freeze filtering rules before any CNN evaluation

**Metrics & QC:**
- Positive count (unknown; estimate ~10k–100k)
- Negative count (depends on strategy)
- Length distribution (should be 8–12 only)
- No class-I to class-II contamination
- Overlap check: any peptide in both positive and negative sets flagged

**Expected Outcome:**
- PXD024871_POSITIVES.csv (peptide, length, source_unit, hla_genotype, …)
- PXD024871_NEGATIVES.csv (peptide, length, generation_method, …)
- Filtering log with statistics

**Limitations:**
- Deposited q ≤ 0.05 may be too lenient; re-filtering changes positive purity
- Negative strategy choice sets ceiling on all downstream metrics
- Shared peptides across donors not yet decided (see leakage section)

**Status:** RESOLVED — D002 and D024 resolved; dataset frozen, G4 passed (run-009)

**Next Step:** Resolve #2, lock class ratio, then execute filtering.

---

## § 9. Leakage Prevention

**Purpose:** Prevent data leakage across train/validation/test splits.

**Why this method is needed:** Leakage produces high performance that means nothing, and it is invisible in the metrics it inflates. It has to be excluded by construction and audited, because no downstream number reveals it.

**Input & Sources:**
- PXD024871_POSITIVES.csv (from Phase B)
- PXD024871_NEGATIVES.csv
- Biological unit definitions (Phase A3)

**Methodology:**
- Verify no exact sequence overlap: test peptides not in train unless intentional
- Check unit-level leakage: no unit contributes to both train and test
- Derived-sequence leakage: no sequences from test peptides enter training as negatives
- Preprocessing: all normalization fitted on training data only

**Metrics & QC:**
- Test set peptides not in train set ✓
- Test set units disjoint from train units ✓
- No cross-split negative generation from test peptides ✓

**Expected Outcome:**
- Leakage audit report
- Split-definition frozen with verification

**Limitations:**
- **Shared-peptide ambiguity**: HLA ligandomes overlap between donors sharing alleles. Same sequence can be genuinely positive in both train and test donors. Unresolved handling: drop cross-split duplicates, or allow and report both ways?

**Status:** RESOLVED — D003 resolved; G5 audited, two failures declared with mandated handling (run-010)

**Next Step:** Decide cross-donor duplicate handling.

---

## § 10. Train/Validation/Test Design

**Purpose:** Split data by biological unit to ensure independent generalization test.

**Why this method is needed:** Splitting by participant is the only design that tests the claim actually being made. A peptide-level split would measure memorisation of a ligandome, not generalization to a new individual.

**Input & Sources:**
- 52 class-I donors with run counts (range: 3–15)
- PXD024871_POSITIVES.csv
- PXD024871_NEGATIVES.csv

**Methodology:**
- Primary design: stratified grouped split by donor
- If donor count sufficient (≥ 8–10): fixed 60/20/20 split
- If insufficient: grouped k-fold cross-validation
- Test set locked, untouched during model selection
- **Allele-disjoint secondary split** (for robustness check: hold out all runs of a specified allele, e.g., HLA-A*02:01, and measure performance)

**Metrics & QC:**
- Train / validation / test donor counts recorded
- Peptide counts per split reported
- Positive:negative ratio consistent across splits
- Donor stratification verified (no unit in multiple splits)

**Expected Outcome:**
- PXD024871_TRAIN.csv, PXD024871_VALIDATION.csv, PXD024871_TEST.csv
- Split statistics (counts, donor breakdown, allele coverage)
- Primary and secondary split definitions documented

**Limitations:**
- Small donor count (52) limits stable fixed splits
- Donor-held-out ≠ allele-held-out: HLA-A*02:01 in 29/52 donors
- Unbalanced run counts (3–15) mean peptide counts dominated by 15-run donor

**Status:** RESOLVED — split frozen, G6 passed (run-011)

**Next Step:** Lock positive/negative counts and class ratio, then define splits.

---

## § 11. CNN Architecture

**Purpose:** Define the network family, fixed before any model is fit.

**Why this method is needed:** A deliberately simple architecture is what makes the result interpretable: if a minimal model finds signal, the signal is in local sequence. A larger model performing well would leave the source of its performance unidentifiable.

**Input & Sources:** Length distribution from run-006; throughput from run-002; compute gate §14.

**Methodology — FROZEN 2026-10-06.** Fixed topology; only the bracketed values vary, and only within the §13 grid.

```
input  (12,) integer-encoded          §12
  -> embedding, dim E                 [E]
  -> conv1d, kernel k, C filters      [k] [C]  -> ReLU
  -> max-pool, size 2
  -> conv1d, kernel k, C filters      [k] [C]  -> ReLU
  -> global max-pool                  -> (C,)
  -> dropout p                        [p]
  -> dense 64 -> ReLU
  -> dense 1  -> sigmoid
```

Two convolutional blocks, not more: the receptive field after two kernel-3 blocks with one pooling step already spans the full 12-residue input, so depth beyond this cannot see more of the peptide and would only add capacity. Global max-pooling is used rather than flattening so the representation is position-invariant at the final layer, forcing positional information to be carried by the convolutions themselves, which is the thing being tested.

**Metrics & QC:** Topology fixed; parameter count reported per configuration; no architecture selected after seeing test performance.

**Expected Outcome:** `cnn_config.json` per run, reproducible from the grid alone.

**Limitations:** A simple family may underperform. Outcome C in proposal §21 (weak CNN, strong existing predictors) remains plausible and is a legitimate result, not a failure of the design.

**Status:** **FROZEN** (D026). Topology cannot change; deviation requires a new decision entry and makes any claim exploratory.

**Next Step:** None.

---

## § 12. Input Representation

**Purpose:** Fix how peptides become model input.

**Why this method is needed:** The representation determines what the model can possibly learn, so it is a scientific choice rather than an implementation detail. Changing it after seeing test performance would invalidate the endpoint.

**Input & Sources:** Union length distribution (run-006): 8-mers 15.47%, 9-mers 27.80%, 10-mers 26.44%, 11-mers 18.67%, 12-mers 11.61%.

**Methodology — FROZEN 2026-10-06.**

Twenty standard amino acids map to integers 1–20 in alphabetical order of one-letter code; 0 is reserved for padding and is a learnable embedding like any other token. Sequences containing any other character were excluded at dataset construction, so none occurs.

**Peptides are padded to length 12 in the centre, not on the right.** The first four residues occupy positions 1–4 and the last four occupy positions 9–12; padding fills the middle. A 12-mer is unpadded; an 8-mer carries four pad tokens at positions 5–8.

This is the one place domain knowledge enters the encoding, and it is declared rather than buried. Class-I binding motifs are anchored at the N-terminal region and at the C-terminus. Right-padding would place the C-terminal residue at a different index for every peptide length, so a convolution would have to learn five separate C-terminal motifs — one per length — from a representation that actively obscures the alignment. Centre-padding costs nothing and removes an artefact. It does not encode which residues matter, only that the two termini are comparable across lengths.

Length is **not** supplied as a separate feature. The pad tokens make it recoverable, and adding it explicitly would let the model exploit any residual length imbalance; the negative set is length-matched exactly, so no such imbalance exists to exploit.

**Metrics & QC:** Encoding deterministic; a round-trip test confirms sequence recovery from the encoding for every length.

**Expected Outcome:** Fixed encoder, shared by every run.

**Limitations:** Centre-padding assumes both termini are the informative regions. That is a strong prior from the biology and would be wrong for a presentation mechanism anchored internally.

**Status:** **FROZEN** (D026).

**Next Step:** None.

---

## § 13. Training Protocol

**Purpose:** Fix every training parameter and the selection rule before fitting.

**Why this method is needed:** Hyperparameters chosen with any sight of the test partition convert a held-out estimate into an optimistic one. Specifying the protocol in advance is what keeps the held-out estimate held out.

**Input & Sources:** Frozen dataset and split; measured throughput (run-002); compute gate §14.

**Methodology — FROZEN 2026-10-06.**

| Parameter | Value |
|---|---|
| Loss | binary cross-entropy |
| Optimizer | Adam, learning rate 1e-3, default betas |
| Batch size | 512 |
| Max epochs | 100 |
| Early stopping | patience 10 on validation average precision |
| Class weighting | none — the classes are 1:1 by construction (D002) |
| Weight init seed | `seed('model_init', replicate)` (D010) |

**Grid — 16 configurations, fixed:**

| Hyperparameter | Values |
|---|---|
| embedding dim `E` | 16, 32 |
| filters `C` | 32, 64 |
| kernel `k` | 3, 5 |
| dropout `p` | 0.0, 0.3 |

2 × 2 × 2 × 2 = 16, within the §14 limit of 20. Learning rate, batch size and dense width are fixed rather than searched: each would multiply the grid for a parameter with far less influence on this architecture than the four above.

**Model selection:** mean validation average precision across the five folds, computed on training folds only. The test partition is not read until the selected configuration is fixed and the endpoint computed once.

**Final fit:** the selected configuration, five folds × five initialisation seeds = 25 runs. All 25 are reported; selecting among seeds is prohibited (D010). **Endpoint (D027):** per-unit average precision is computed under each model and averaged across the 25; the estimand is the mean of those per-unit values, bootstrapped over units. Score-ensembling is reported as a secondary figure, since an ensemble answers a more flattering question than §25 asks.

**Reduction ladder priority (required by D022).** If compute is exceeded, configurations drop from 16 to 8 by removing the `E = 16` half first, then `p = 0.0`. Order fixed here so it cannot be chosen under pressure.

**Compute check:** 16 × 5 = 80 selection runs plus 25 final = **105 runs**, within the 150 cap. At 8.5 s/epoch and 100 epochs that is **24.7 h** against a 96 h cap, or roughly 10 h with early stopping at typical depth.

**Metrics & QC:** Every run records config, seed, epochs to stop, and per-fold validation AP. No run touches the test partition.

**Expected Outcome:** `CNN_PREREGISTRATION.md` emitted from this specification; `training_log.csv` per run.

**Limitations:** A 16-point grid may miss a better configuration. That is accepted: a larger search increases the chance of selecting on noise, and the endpoint is about whether sequence carries signal, not about the best attainable model.

**Status:** **FROZEN** (D026).

**Next Step:** None. Training may proceed on hardware meeting §14.

---

## § 14. Compute Gate

**Purpose:** Define computational budget and ensure experiment fits within resource constraints.

**Why this method is needed:** An unbounded compute budget means the design silently expands until something works, which is selection. A declared budget forces any reduction to be recorded as a decision instead.

**Input & Sources:**
- Measured throughput, run-002: **122,648 peptides/sec** training, 4 cores, no GPU
- Measured peptide yield, run-004/005: **~16,500 unique 8–12mers per acquisition**
- Measured cross-unit redundancy, run-005: **2.9–6.2% pairwise overlap**, Heaps' β ≈ 0.92
- **Projected eligible positives at 52 units: ~1.9M** (see limitations — this is a projection from 4 units)
- Machine: 4 cores, 15 GiB, no GPU, **ephemeral session container**

**Methodology — RESIZED 2026-10-06 (D022).** The original gate was sized at a
100,000-positive worst case. Measurement puts the real figure near **1.9
million**, a 19× error, so the budget is rebuilt from the measured numbers.

**Resized again 2026-10-06** on the measured union (2,658,972) and the D024 cap. The uncapped grid costs 120 h at 1:1; at the cap it is **23.6 h**, comfortably inside the budget and executable on hardware that exists.

Grid cost, 20 configurations × 5 folds × 100 epochs = 100 runs:

| Positives | 1:1 ratio | 1:10 ratio |
|---|---|---|
| 500,000 | 22.6 h | 124.6 h |
| 1,000,000 | 45.3 h | 249.1 h |
| 1,900,000 | 86.1 h | 473.5 h |

**The class ratio is a 5.5× compute lever.** This is new information for D002:
run-001's F4 and F6 already argued against wide ratios on bias and precision
grounds, and compute now points the same way. 1:1 is preferred on all three.

| Limit | Value | Change |
|---|---|---|
| Planning worst case | **520,000 positives** (52 units × 10,000 cap, D024) | measured union is 2,658,972; capped on the precision curve, not for budget |
| Class ratio assumed | **1:1** | was 1:10; D002 recommendation strengthened |
| Max hyperparameter configurations | **20** | unchanged |
| Max epochs per run | **100**, patience 10 | unchanged |
| Max folds | **5** | unchanged |
| Max seeds, selected config | **5** | unchanged |
| Max total training runs | **150** | unchanged |
| Max wall-clock | **96 hours** | was 48 h |
| CPU allocation | **4 cores** | unchanged |
| GPU allocation | **0 available** | unchanged, and now the binding constraint |
| Peak disk, extraction | **~12 GiB** | unchanged (D021) |
| Transfer budget, S3 | **47.85 GiB, ~9 h at 1.5 MiB/s measured** | newly specified |

**The honest conclusion: the work has outgrown this environment.** At 1:1 and 2M
positives the grid is ~90 hours. The session container is **ephemeral** — it is
reclaimed after inactivity — so a 90-hour grid cannot run here at all,
regardless of the cap. Raising the cap to 96 h makes the budget arithmetically
consistent; it does not make it executable on this machine.

Three ways out, in preference order:

1. **A GPU.** The architecture is small; the cost is row throughput, not model
   size. This is the change that makes the design comfortable rather than
   marginal, and run-002 already established no GPU is *needed* for a small
   dataset — that conclusion does not survive a 19× larger one.
2. **Persistent hardware** with equivalent CPU. 90 hours is fine on a machine
   that is not reclaimed; it is impossible on one that is.
3. **Shrink the design.** The reduction ladder below, or subsampling positives.
   Subsampling is a design change requiring its own decision, not a budget
   adjustment.

**Predefined reduction ladder** (unchanged in order; it now triggers much
earlier). Applied in order, each step recorded:
1. Seeds for the selected config, 5 → 3
2. Configurations, 20 → 10, by a priority order fixed at preregistration
3. Folds, 5 → 3
4. Epochs 100 → 50, patience 10 → 5

At 1M positives and 1:10 the full ladder still leaves 37 h; at 1:1 it leaves
6.8 h. The ladder alone cannot rescue a wide class ratio at this dataset size.

**Never reduced:** the test partition, the split definition, or the
allele-disjoint secondary analysis. Those are the design, not the budget.

**Metrics & QC:**
- Worst-case grid < wall-clock cap ✓ at 1:1 (86 h vs 96 h) ✗ at 1:10 (474 h)
- Peak extraction disk < available ✓ (~12 GiB vs 30 GB)
- Transfer feasible within session lifetime ✗ **9 h transfer on an ephemeral container is a live risk**
- Any ladder step taken is recorded with the measurement that triggered it

**Expected Outcome:**
- Budget fixed before any model is fit, from measured rather than assumed inputs
- The hardware requirement is stated explicitly rather than discovered at run time

**Limitations:**
- **The 1.9M projection comes from 4 units of 52.** Heaps' β ≈ 0.92 is fitted on
  four points; the 52-unit figure is an order of magnitude, not an estimate.
  Marginal novelty was still 92% at the fourth unit, so saturation is not near,
  but the exponent could move materially with more units.
- ~~Only one of six sampled pairs shared alleles.~~ **Settled 2026-10-06** with a
  fifth unit: 10 pairs, 4 of which share alleles including one HLA-A\*02:01 pair.
  Shared-allele pairs overlap a mean 4.8% against 4.0% for disjoint pairs — a
  factor of 1.21, so the sample was *not* unusually novel and the projection is
  not a selection artifact. β rose slightly to 0.959, projecting 2.07M, which
  the 2,000,000 planning figure covers.
- **Open interpretive question raised by that result.** Overlap barely tracks
  shared alleles, which is surprising if presentation is allele-determined. The
  parsimonious explanation is sampling depth: each unit samples ~16,500 peptides
  from a far larger presented repertoire, so even identical repertoires would
  overlap little by chance. If that is right, "generalizes to an unseen unit"
  partly tests generalization across *samples of* a repertoire rather than
  across repertoires, which weakens the §25 reading further. Testable signature:
  overlap should rise with per-unit depth. Not resolvable from this data.
- Throughput is numpy over BLAS, an upper bound on time; a real framework is faster.
- Training cost taken as 3× forward.
- Numbers are specific to this machine and do not port.

**Status:** RESOLVED — resized from measurement (D022, run-005). **Flagged:** the
budget is arithmetically consistent but not executable on this hardware.

**Next Step:** Decide the hardware question before the preregistration freeze.
Re-check the projection once more units are extracted.

---

## § 15. Primary Endpoint

**Purpose:** Define primary performance metric and secondary metrics for evaluation.

**Why this method is needed:** The primary metric must be fixed in advance or the best of several becomes the reported one. Run-001 further showed the chosen metric is only interpretable alongside a fixed class ratio, since its baseline is the prevalence.

**Input & Sources:**
- Test set predictions (from trained CNN)
- Test set labels (positive / negative)

**Methodology:**
- Primary metric: AUPRC (Area Under Precision-Recall Curve)
  - Justification: accounts for class imbalance
  - Baseline = positive prevalence (must be locked in Phase B)
- Secondary metrics: AUROC, sensitivity, specificity, precision, recall, F1, balanced accuracy, calibration

**Metrics & QC:**
- Primary metric locked during preregistration
- Baseline (positive prevalence) recorded
- Secondary metrics computed for completeness

**Expected Outcome:**
- AUPRC on test set
- Full confusion matrix and secondary metrics
- Uncertainty intervals (via bootstrap, see § 16)

**Limitations:**
- AUPRC is incomparable across studies with different class ratios
- Positive prevalence must not change after observing test performance

**Status:** RESOLVED — AUPRC primary at 1:1; floor is the measured 0.597, not prevalence (D002, D008)

**Next Step:** Lock positive:negative ratio, then freeze primary endpoint.

---

## § 16. Statistical Evaluation

**Purpose:** Distinguish peptide-level from biological-unit-level independence and provide uncertainty intervals.

**Why this method is needed:** Peptide-level and participant-level uncertainty answer different questions, and conflating them overstates precision by a wide margin. Run-001 quantified this: resolution is bounded by participant count, and bootstrap replicates do not affect it.

**Input & Sources:**
- Test set predictions and labels
- Unit membership for each test peptide
- Cluster bootstrap configuration (B=10,000, seed=20261006)

**Methodology:**
- Report peptide-level performance (e.g., AUPRC on all test peptides)
- Report donor-level performance (aggregate by donor, report median, range, IQR)
- Use cluster bootstrap: resample donors (not peptides), compute metric on each bootstrap sample
- Record resampling unit explicitly (donors, not peptides)
- Seed = 20261006 (today's date, 2026-10-06; record convention)

**Metrics & QC:**
- Bootstrap intervals stable (B=10,000)
- Metric computed identically on each bootstrap sample
- Donor-level disaggregation shown

**Expected Outcome:**
- Pooled AUPRC with 95% CI
- Donor-level summary: median, min, max, IQR
- Bootstrap distribution plot
- bootstrap_results.json (all bootstrap replicates)

**Limitations:**
- Uncertainty capped by donor count (52), not B
- Tight-looking intervals may hide instability across donors

**Status:** OPEN (depends on test evaluation)

**Next Step:** Execute after model training and test evaluation.

---

## § 17. Donor-Level Evaluation

**Purpose:** Verify generalization across biological individuals, not just pooled peptide counts.

**Why this method is needed:** A pooled number can be carried entirely by the heaviest-contributing participants. Per-participant reporting is the only way to see whether performance generalizes across individuals or merely across peptides.

**Input & Sources:**
- Test set from donors not in training
- Model trained on training donors only

**Methodology:**
- For each held-out donor, compute performance separately (if sample size permits)
- Summarize across donors: median, range, uncertainty interval
- Flag donors with outlier performance

**Metrics & QC:**
- Minimum 8–10 held-out donors (depends on primary split)
- Performance reported per donor
- No held-out donor in training data

**Expected Outcome:**
- donor_level_metrics.csv (donor, AUPRC, AUROC, N_peptides, …)
- Distribution plot (median ± range across donors)
- Outlier analysis

**Limitations:**
- Donors with few test peptides have noisy estimates

**Status:** OPEN (depends on test evaluation)

**Next Step:** Compute after model evaluation.

---

## § 18. Comparison With Existing T-A4 Predictors

**Purpose:** Benchmark CNN against existing predictors on identical peptide rows. Preregistered as the **secondary** endpoint per D014 (ratified), reported regardless of what §25 shows.

**Why this method is needed:** An absolute performance figure has no interpretable scale. Comparison on identical rows is what converts it into a statement about whether this approach adds anything over what already exists.

**Input & Sources:**
- Same test-set peptides used for CNN evaluation
- Existing T-A4 predictors (NetMHCpan, MixMHCpred, or others)
- IEDB training set membership (to check for contamination)

**Methodology:**
- Obtain predictions from existing predictors for same test peptides
- **Contamination check**: Verify test peptides are not in existing predictor training data
- Compute performance metrics (AUPRC, AUROC, etc.) for all predictors on identical rows
- No predictor receives a selectively easier dataset

**Metrics & QC:**
- Same test set for all predictors ✓
- Test peptides not in T-A4 or IEDB training data ✓
- Performance metrics comparable (same class ratio, same evaluation protocol)

**Expected Outcome:**
- comparison_with_predictors.csv (predictor, AUPRC, AUROC, …)
- Comparison summary and interpretation

**Limitations:**
- Existing predictors designed for different tasks (binding affinity vs. presence/absence)
- Fair comparison requires careful setup

**Status:** OPEN (depends on test evaluation)

**Next Step:** Resolve D006 first — the contamination check in M7 gates both the fairness of this comparison and any future promotion of it to primary. Then obtain predictor outputs and evaluate. Better powered than §25 at every participant count tested (run-001, F7), but not promotable post hoc: a switch after seeing results is endpoint switching regardless of the power argument.

---

## § 20. Biological Interpretation

**Purpose:** Interpret CNN performance in biological context with appropriate caveats.

**Why this method is needed:** Performance above chance has several possible causes besides the intended one, including batch, platform and donor effects. Interpretation has to exclude the alternatives explicitly or the biological reading is unsupported.

**Input & Sources:**
- CNN performance results (held-out donor evaluation)
- Leakage checks (passed)
- Negative-control design
- Comparison with existing predictors

**Methodology:**
- Assess whether performance > chance supports reproducible sequence information
- Distinguish genuine sequence motifs from dataset artifacts, donor effects, technical biases
- Consider instrument confounds, allele specificity, run imbalance
- Report robustness across donors, peptide lengths, negative-control designs

**Metrics & QC:**
- Biological unit generalization verified ✓
- Leakage checks all passed ✓
- Confound analysis complete

**Expected Outcome:**
- CNN_RESULTS.md with interpreted findings
- Caveats and limitations clearly stated
- Support for or against primary hypothesis

**Limitations:**
- Outcome C (weak CNN) plausible; interpretation may be null
- High performance does not prove experimental binding

**Status:** OPEN (depends on test evaluation and all QC gates)

**Next Step:** Execute after all results are available.

---

## § 25. Primary Hypothesis

**Purpose:** State testable hypothesis with explicit decision threshold.

**Why this method is needed:** A hypothesis without a threshold cannot fail. Run-001 demonstrated this concretely: as worded, the hypothesis passes for a classifier of negligible value, so it needs a stated effect size to carry information.

**Input & Sources:**
- Preregistered primary metric and test protocol
- Minimum effect size and sample size

**Methodology:**
- Primary hypothesis: CNN performs better than chance on held-out donors
- Decision rule: AUPRC > baseline + [effect size threshold, e.g., 0.10 or 0.05]
- Alternative: "no reproducible sequence signal detected"

**Metrics & QC:**
- Hypothesis clearly falsifiable
- Decision threshold locked before test evaluation
- Effect size justified or acknowledged as exploratory

**Expected Outcome:**
- Hypothesis rejected or supported
- Interpretation consistent with evidence

**Limitations:**
- "Better than chance" undefined without threshold
- Small donor count may prevent robust effect estimation

**Status:** RESOLVED — primary endpoint per D014; decision rule fixed by D008: reject if the lower bound of a nominal-99% cluster-bootstrap interval exceeds 0.647 (composition floor 0.597 + 0.05). Nominal 99% because 95% delivers only ~89% actual coverage at 10 test units

**Next Step:** None. The rule is preregistered. Note its limitation: power is 0.42 at AUROC 0.70, so the minimum reliably detectable effect is a lift of ~0.14 AP (AUROC ≈ 0.75). Failure to reject is not evidence of no signal.

---

## Summary: QC Gate Schedule

```
G1 — Dataset inventory verified                          § 5A1
G2 — File map complete with HLA allotypes                § 5A2 [BLOCKER #1]
G3 — Biological units resolved                           § 5A3
G4 — Positive/negative sets frozen                       § 6   [BLOCKER #2]
G5 — Leakage checks passed + confound analysis          § 9
G6 — Train/validation/test split locked                 § 10
G7 — CNN architecture & input representation locked     § 11–12
G8 — Training protocol & compute gate passed            § 13–14
G9 — CNN training completed                             (training)
G10 — Test evaluation completed                         § 15–17
G11 — Predictor comparison completed                    § 18
G12 — Statistical analysis completed                    § 16
G13 — Biological interpretation finalized               § 20
FINAL → Decision on primary hypothesis                  § 25
```

No gate can be bypassed silently. Record any reduction or deferral.
