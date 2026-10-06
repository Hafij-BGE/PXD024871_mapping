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
- 47.8 GB .msf files require streaming extraction
- SDRF has 402 rows; 504 files include non-MS-run files

**Status:** OPEN (not yet started)

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

**Status:** OPEN (blocked on HLA allotype decision, see DECISION_LOG #1)

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

**Status:** OPEN (depends on A2)

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

**Status:** OPEN (blocked on DECISION_LOG #2 and class-ratio lock)

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

**Status:** OPEN (blocked on shared-peptide decision in DECISION_LOG)

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

**Status:** OPEN (depends on Phase B and shared-peptide decision)

**Next Step:** Lock positive/negative counts and class ratio, then define splits.

---

## § 11. CNN Architecture

**Purpose:** Define simple 1D CNN to test whether sequence-local information provides predictive signal.

**Why this method is needed:** A deliberately simple architecture is what makes the result interpretable: if a minimal model finds signal, the signal is in local sequence. A larger model that performed well would leave the source of its performance unidentifiable.

**Input & Sources:**
- Sequence length distribution from Phase B
- Amino-acid encoding scheme (frozen)
- Architecture reference: standard 1D CNN with convolutions, pooling, dense layer

**Methodology:**
- Define embedding or numerical representation per amino acid
- Specify convolutional blocks (kernel size, filters, stride)
- Specify pooling (type, size)
- Specify dense layers and output
- Keep architecture intentionally simple to isolate sequence signal

**Metrics & QC:**
- Architecture documented in cnn_config.json
- Reproducible from configuration alone
- No data observed during architecture selection

**Expected Outcome:**
- cnn_config.json (full architecture specification)
- Architecture diagram or description

**Limitations:**
- Simplicity may underperform compared to more complex models
- Outcome C (weak CNN) plausible on ~10k peptides

**Status:** OPEN (depends on Phase B for sequence statistics)

**Next Step:** Observe sequence length distribution, finalize architecture.

---

## § 12. Input Representation

**Purpose:** Define how peptide sequences are converted to numerical form and how variable lengths are handled.

**Why this method is needed:** The representation determines what the model can possibly learn, so it is a scientific choice rather than an implementation detail. Changing it after seeing test performance would invalidate the endpoint.

**Input & Sources:**
- Sequence length range (expected: 8–12)
- Amino-acid alphabet (20 standard + gaps)

**Methodology:**
- Choose representation: one-hot encoding, embedding vectors, BLOSUM, or learned embedding
- Choose length handling: padding, truncation, or length-aware layer
- Freeze representation before evaluating test performance
- Document exact implementation

**Metrics & QC:**
- Representation is deterministic
- No hyperparameter tuning on test data
- All sequences transformable without data leakage

**Expected Outcome:**
- Input representation scheme documented
- Example transformed sequences shown
- Implementation code or reference

**Limitations:**
- Fixed-length padding assumes variable-length peptides
- Representation choice not validated on real data until model training

**Status:** OPEN (depends on Phase B)

**Next Step:** Finalize representation, document exactly.

---

## § 13. Training Protocol

**Purpose:** Specify all hyperparameters and training control before running experiments.

**Why this method is needed:** Hyperparameters chosen with any sight of the test partition convert a held-out estimate into an optimistic one. Specifying the protocol in advance is what keeps the held-out estimate held out.

**Input & Sources:**
- Training data (from Phase B split)
- Validation data (from Phase B split)
- Preregistration (frozen before model training)

**Methodology:**
- Lock optimizer, learning rate, batch size, epochs, early stopping rule
- Lock loss function, random seed, class weighting
- Define hyperparameter search space and cross-validation strategy
- Model selection criterion uses training/validation only
- Test set never used for model selection

**Metrics & QC:**
- Preregistration document with all parameters locked
- Seed and date recorded
- Hyperparameter search bounded (max runs, max epochs)

**Expected Outcome:**
- CNN_PREREGISTRATION.md (locked parameters)
- cnn_seed.json (random seed, date, model selection criterion)

**Limitations:**
- Search space bounds may be conservative
- Early stopping rule may fail on small datasets

**Status:** OPEN (depends on Phase B and compute gate)

**Next Step:** Define compute budget, freeze preregistration.

---

## § 14. Compute Gate

**Purpose:** Define computational budget and ensure experiment fits within resource constraints.

**Why this method is needed:** An unbounded compute budget means the design silently expands until something works, which is selection. A declared budget forces any reduction to be recorded as a decision instead.

**Input & Sources:**
- Measured throughput on the target machine: `results/compute/benchmark.json`, run-002
- Machine: 4 cores, Intel Xeon @ 2.10 GHz, 15 GiB RAM, **no GPU**
- Measured training throughput: **122,648 peptides/sec** for the §11 architecture
- Available writable disk: 30 GB
- **[provisional]** identification containers described as ~47.8 GB in total

**Methodology:**
Limits derived from measurement, not assumption. Worst-case sizing assumes 100,000 eligible positives at a 1:10 class ratio — 1.1M rows per epoch, 9.0 s/epoch, 14.9 min per 100-epoch run.

| Limit | Value | Basis |
|---|---|---|
| Max hyperparameter configurations | **20** | Grid cost below |
| Max epochs per run | **100**, early-stopping patience 10 | Convergence expected far sooner at this model size |
| Max cross-validation folds | **5** | Participant count will not support more stable folds |
| Max seeds, selected config only | **5** | Search runs at 1 seed |
| Max total training runs | **150** | 20 configs × 5 folds = 100 for selection; 1 config × 5 folds × 5 seeds = 25 for the final fit; 25 spare |
| Max wall-clock | **48 hours** | Worst case is ~31 h; see grid |
| CPU allocation | **4 cores** | All that exists |
| GPU allocation | **0** | None available, and the measurement shows none is needed |
| Peak disk, extraction | **~2 GB** | One container plus its extract at a time |

Grid cost at the worst-case size: selection 25 h, final fit ~6 h, total ~31 h against a 48 h cap.

**Predefined reduction ladder.** Applied in this order if the cap is reached, each step recorded as a decision:
1. Seeds for the selected config, 5 → 3
2. Hyperparameter configurations, 20 → 10, dropped by a priority order fixed at preregistration
3. Cross-validation folds, 5 → 3
4. Epochs 100 → 50, patience 10 → 5

**Never reduced:** the test partition, the split definition, or the allele-disjoint secondary analysis. Those are the design, not the budget, and cutting them to fit a budget would be changing the experiment to afford it.

**Metrics & QC:**
- Worst-case grid cost < wall-clock cap ✓ (~31 h vs 48 h)
- Peak extraction disk < available ✓ (~2 GB vs 30 GB)
- Full container set > available disk ✓ **confirms streaming is mandatory, not an optimisation** (~47.8 GB [provisional] vs 30 GB)
- Any reduction-ladder step taken is recorded with the measurement that triggered it

**Expected Outcome:**
- Budget fixed before any model is fit, so no run can be justified retrospectively
- Reduction, if needed, is a logged decision rather than a silent design change

**Limitations:**
- Throughput measured with numpy over BLAS, not an optimised framework. Conservative by construction: a real framework should be faster, so the budget has headroom rather than a shortfall.
- Training cost taken as 3× forward, the standard approximation; the true factor varies with optimiser and implementation.
- The 100,000-positive worst case is an assumption. The real eligible count is unknown and gates on D007; a smaller set makes every figure here slack.
- Measured on this cloud machine. If the work moves to different hardware, run-002 must be re-executed and the budget reset — the ladder is valid, the numbers are not portable.
- No GPU was available to measure. If one is used later, these limits understate what is affordable.

**Status:** RESOLVED — budget set from measurement (D020, run-002). Reopens if the hardware changes.

**Next Step:** None for this section. The worst-case sizing is re-checked once D007 fixes the real eligible count.

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

**Status:** OPEN (blocked on class-ratio decision in DECISION_LOG)

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

**Status:** OPEN — remains the primary endpoint per D014 (ratified); the threshold itself is still unspecified and blocked on D002

**Next Step:** Preregister the decision rule in the form D014 fixes — a lift over prevalence, tested on the interval's lower bound. The magnitude cannot be set until D002 fixes the class ratio, since prevalence follows from it. Run-001 indicates ~0.10 AP is cleanly resolvable at ten held-out participants and ~0.04 is marginal.

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
