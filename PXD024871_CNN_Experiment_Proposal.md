# PXD024871 CNN Experiment Proposal

**Project:** T-A4  
**Experiment:** PXD024871 sequence-based CNN experiment  
**Status:** Proposal — not yet preregistered or executed

## 1. Purpose

Define a standalone CNN experiment using PXD024871 to test whether a sequence-based 1D CNN can learn peptide sequence patterns associated with experimentally observed HLA class-I-associated peptides and generalize to previously unseen biological units.

The CNN experiment is separate from provenance/mapping.

```text
PXD024871
    ↓
PROVENANCE / FILE MAPPING
    ↓
eligible HLA-I peptide set
    ↓
dataset construction
    ↓
CNN
    ↓
unseen-unit evaluation
    ↓
comparison with existing T-A4 predictors
```

The CNN must not be used to determine which raw files are HLA class-I files or which files belong to which donor.

## 2. Primary Research Question

> Can a peptide-sequence CNN distinguish experimentally observed HLA class-I-associated peptides from appropriately constructed negative controls, and does the learned sequence signal generalize to previously unseen biological units?

## 3. Secondary Research Questions

1. Can the CNN learn reproducible sequence patterns from PXD024871?
2. Does performance remain when entire biological units/donors are withheld from training?
3. How does the CNN perform relative to the existing T-A4 binding predictors on identical peptide rows?
4. Does validated PXD024871 data materially increase the sequence space represented by T-A4?
5. Are CNN results robust across donors, datasets, peptide lengths, and negative-control constructions?

## 4. Relationship to O9

PXD024871 currently has a **potential marginal gain of 7,371 sequences**. This is not yet a validated contribution to the T-A4 core.

```text
7,371
   ↓
potential sequence gain
   ↓
NOT automatically the CNN dataset
```

The dataset must first be mapped and its eligible subset established.

## 5. Phase A — Provenance and File Mapping

### A1. Obtain the Dataset Inventory

Collect and preserve:

- complete PXD024871 file inventory
- SDRF
- relevant metadata
- peptide identification files
- experimental description
- accession information
- available checksums

Record retrieval date, source, accession, file identity, and provenance.

### A2. Build the File Map

Create a file-level mapping table containing at least:

| Field | Meaning |
|---|---|
| `raw_file` | Deposited raw file |
| `sample_id` | Experimental sample |
| `unit_id` | Normalized biological unit |
| `replicate` | Technical/biological replicate |
| `fraction` | Fraction, if applicable |
| `hla_class` | Class-I / class-II / unknown |
| `tissue` | Biological material |
| `organism` | Organism |
| `source_evidence` | Metadata supporting classification |
| `eligible` | Yes / no / unknown |
| `exclusion_reason` | Reason for exclusion |

Class must be established from experimental metadata/depositor evidence, not guessed from filenames.

### A3. Resolve Biological Units

Raw files are not automatically equivalent to donors.

```text
Donor 01
 ├── replicate 1
 ├── replicate 2
 └── fraction 1
```

may represent one biological unit.

The normalized `unit_id` must therefore be established before model splitting or donor counting.

## 6. Phase B — Define the CNN Dataset

After provenance mapping:

```text
eligible HLA-I files
        ↓
validated peptide identifications
        ↓
quality filtering
        ↓
unique peptide set
        ↓
positive examples
```

Peptide filtering rules must be frozen before examining CNN performance.

Potential retained fields:

- peptide sequence
- peptide length
- sample
- biological unit
- dataset
- HLA context
- identification confidence
- source file

## 7. Positive Examples

The positive class consists of experimentally observed peptides that satisfy the predefined PXD024871 HLA-I eligibility and peptide-quality criteria.

Not every sequence in the deposited material is automatically positive.

## 8. Negative Controls

Negative controls must be defined before model training.

Candidate strategies:

### Negative set A — Reference-derived controls

Generate peptides from the appropriate reference background while matching relevant properties such as peptide length and, where appropriate, amino-acid composition.

### Negative set B — Decoy controls

Use appropriately generated sequence decoys while preventing accidental overlap with positive examples.

### Negative set C — Hard negatives

Where scientifically justified, use peptides that resemble positives but were not experimentally observed.

The primary negative-control strategy must be selected before training.

## 9. Leakage Prevention

### Exact sequence leakage

Test peptides must not be present in training data unless repeated observations are intentionally part of the predefined design.

### Biological-unit leakage

No biological unit may contribute peptides to both training and test sets.

```text
TRAIN
Donor 1
Donor 2
Donor 3

TEST
Donor 4
Donor 5
```

### Derived-sequence leakage

Sequences derived from test peptides must not enter training as negative or augmented examples.

### Preprocessing leakage

Any learned transformation or normalization must be fitted using training data only.

## 10. Train / Validation / Test Design

The primary design should split data by biological unit.

The exact proportions depend on the number of eligible independent units.

If the number of units is insufficient for a stable fixed split, use grouped cross-validation rather than treating individual peptides as independent biological observations.

The test set must remain untouched during model selection.

## 11. CNN Architecture

Use a sequence-based 1D CNN:

```text
Peptide sequence
      ↓
amino-acid encoding
      ↓
embedding / numerical representation
      ↓
1D convolution
      ↓
activation
      ↓
pooling
      ↓
additional convolutional block(s)
      ↓
global pooling
      ↓
dense layer
      ↓
output probability
```

The architecture should remain sufficiently simple to test whether sequence-local information provides predictive signal.

## 12. Input Representation

Each amino acid will be converted into a predefined numerical representation.

Variable peptide lengths require a predefined handling strategy, such as:

- fixed-length padding,
- length-aware representation,
- or another preregistered method.

The representation must not be changed after observing test performance.

## 13. Training Protocol

Before training, specify:

- optimizer
- learning rate
- batch size
- maximum epochs
- early stopping rule
- loss function
- random seed
- class weighting, if required
- hyperparameter search space
- model-selection criterion

Hyperparameter selection must use training/validation data only.

The held-out test set must not be used for model selection.

## 14. Compute Gate

The CNN experiment will have a predefined computational budget.

Record:

- maximum training runs
- maximum epochs
- maximum wall-clock time
- maximum CPU/GPU allocation
- maximum hyperparameter configurations

If the full design exceeds the predefined limit:

```text
Full experiment
      ↓
compute gate
      ↓
failure?
      ↓
predefined reduction
```

Any reduction must be recorded rather than silently changing the design.

## 15. Primary Endpoint

A proposed primary performance metric is:

> **Area under the precision-recall curve (AUPRC).**

Secondary metrics:

- AUROC
- sensitivity
- specificity
- precision
- recall
- F1
- balanced accuracy
- calibration

The final primary endpoint must be locked during preregistration.

## 16. Statistical Evaluation

Distinguish peptide-level observations from biological-unit-level independence.

Report:

```text
peptide-level performance
        +
biological-unit/donor-level uncertainty
```

Where applicable, use the established T-A4 bootstrap framework:

- cluster bootstrap
- B = 10,000
- seed = 20261006
- resampling unit recorded explicitly

Any deviation must be documented.

## 17. Donor-Level Evaluation

For every held-out biological unit, report performance separately where sample size permits.

Summarize:

- median performance
- distribution across units
- uncertainty interval
- best-performing unit
- worst-performing unit

The purpose is to determine whether performance generalizes across biological individuals rather than being driven by pooled peptide counts.

## 18. Comparison With Existing T-A4 Predictors

The CNN is one predictor among the existing T-A4 predictors. It is not a replacement for the T-A4 methodology and is not a separate data-processing branch.

```text
Same peptide rows
      ↓
┌────────────┬────────────┬────────────┐
│ Predictor 1│ Predictor 2│    CNN     │
└────────────┴────────────┴────────────┘
      ↓
same evaluation framework
      ↓
performance comparison
```

No predictor should receive a selectively easier dataset.

## 19. Confirmatory vs Exploratory Analyses

### Confirmatory

- predefined CNN architecture family
- predefined biological-unit split
- predefined negative controls
- predefined primary metric
- predefined statistical analysis
- predefined comparison with existing predictors

### Exploratory

- alternative architectures
- alternative embeddings
- motif visualization
- saliency analysis
- peptide-length analysis
- alternative negative-control designs
- architecture ablations

Exploratory findings must not be presented as preregistered confirmation.

## 20. Biological Interpretation

If the CNN performs better than chance, this supports the presence of reproducible predictive information in peptide sequence.

It does **not**, by itself, prove experimental binding.

The CNN could learn genuine sequence motifs, donor-specific patterns, dataset-specific effects, technical artefacts, or other correlations.

Interpretation must therefore consider:

- held-out biological units
- negative controls
- leakage checks
- comparison with existing predictors
- robustness analyses

## 21. Possible Outcomes

### Outcome A — Strong CNN + strong unseen-unit generalization

Supports reproducible sequence-level predictive signal.

### Outcome B — Strong pooled performance + poor unseen-unit performance

Suggests possible donor- or dataset-specific overfitting.

### Outcome C — CNN weak, existing predictors strong

Suggests that the selected CNN representation or architecture is insufficient.

### Outcome D — All predictors weak

May indicate weak sequence signal, difficult controls, dataset limitations, or upstream data issues.

### Outcome E — Extremely strong CNN + failed leakage/control checks

The result must not be interpreted biologically until the problem is resolved.

## 22. PXD024871's Role in T-A4

PXD024871 should initially be classified as:

```text
HIGH POTENTIAL SEQUENCE VALUE
          +
ELIGIBILITY NOT YET ESTABLISHED
```

The current 7,371 marginal-gain value is therefore a **potential contribution**, not a confirmed final contribution.

After mapping:

```text
PXD024871
    ↓
validated eligible subset
    ↓
unique sequence contribution
    ↓
updated union
    ↓
updated coverage
    ↓
CNN experiment
```

Do not report "~60% coverage" as a final result until the eligible file subset and union are validated.

## 23. Expected Reproducible Outputs

### Provenance

```text
PXD024871_FILE_MAP.csv
PXD024871_PROVENANCE.json
PXD024871_ELIGIBILITY.csv
```

### Dataset

```text
PXD024871_POSITIVES.csv
PXD024871_NEGATIVES.csv
PXD024871_TRAIN.csv
PXD024871_VALIDATION.csv
PXD024871_TEST.csv
```

### Model

```text
cnn_config.json
cnn_seed.json
cnn_model/
training_log.csv
```

### Results

```text
cnn_metrics.json
cnn_predictions.csv
donor_level_metrics.csv
comparison_with_predictors.csv
bootstrap_results.json
```

### Documentation

```text
CNN_PREREGISTRATION.md
CNN_METHODS.md
CNN_RESULTS.md
CNN_LIMITATIONS.md
```

## 24. Quality-Control Gates

```text
G1 — Dataset retrieval verified
        ↓
G2 — Complete file inventory
        ↓
G3 — SDRF/file mapping complete
        ↓
G4 — Biological units resolved
        ↓
G5 — HLA-I eligibility resolved
        ↓
G6 — Peptide QC passed
        ↓
G7 — Positive/negative construction frozen
        ↓
G8 — No train/test leakage
        ↓
G9 — Compute gate passed
        ↓
G10 — CNN training completed
        ↓
G11 — Held-out evaluation completed
        ↓
G12 — Statistical analysis completed
        ↓
G13 — Predictor comparison completed
        ↓
FINAL INTERPRETATION
```

A failed gate must be recorded rather than silently bypassed.

## 25. Primary Hypothesis

> **A CNN trained on experimentally observed HLA class-I-associated peptide sequences will perform better than chance on held-out biological units, demonstrating reproducible sequence-level predictive information.**

### Secondary hypothesis

> **The CNN will retain predictive performance when evaluated on biological units not represented in the training data.**

## 26. Explicit Non-Claims

This experiment does **not** claim that:

- CNN mapping replaces metadata mapping.
- PXD024871 automatically belongs in the current T-A4 core.
- 7,371 sequences are already validated as additional coverage.
- CNN predictions are equivalent to experimental binding measurements.
- high peptide-level accuracy proves biological generalization.
- the CNN replaces the existing T-A4 predictors.

## 27. Final Experimental Architecture

```text
                    PXD024871
                        │
                        ▼
              ┌──────────────────┐
              │ PROVENANCE MAP   │
              │ files → samples  │
              │ → units → HLA-I  │
              └────────┬─────────┘
                       │
                 eligible data
                       │
                       ▼
              ┌──────────────────┐
              │ PEPTIDE QC       │
              │ positives        │
              │ matched negatives│
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ GROUPED SPLIT    │
              │ by biological    │
              │ unit/donor       │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │      1D CNN      │
              │ sequence → score │
              └────────┬─────────┘
                       │
                       ▼
          ┌──────────────────────────┐
          │ HELD-OUT EVALUATION      │
          │ AUPRC / AUROC / etc.     │
          └────────────┬─────────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      donor-level QC       predictor comparison
             │                   │
             └─────────┬─────────┘
                       ▼
               FINAL INTERPRETATION
```

## 28. Core Methodological Rule

> **Map the dataset → establish eligible biological units → construct the experiment → train the CNN → evaluate it on unseen units → compare it with the existing predictors.**

The CNN must not be used to solve a provenance problem.
