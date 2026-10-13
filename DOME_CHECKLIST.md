# DOME checklist

Walsh I, Fishman D, Garcia-Gasulla D, et al.; ELIXIR Machine Learning Focus
Group. **DOME: recommendations for supervised machine learning validation in
biology.** *Nat Methods* 2021;18(10):1122–1127.
doi:10.1038/s41592-021-01205-4. Items follow the paper's Box 1 question set
under Data, Optimization, Model and Evaluation.

One dataset and one trained model, so the per-dataset and per-model sections
are given once. Every question is answered; inapplicable ones say why.

---

## Data

**Provenance.** PRIDE **PXD024871**, a published HLA class-I immunopeptidomics
deposit of 52 participants. Identifications are the depositors' own search
output at 5% FDR, **not re-searched here** — L5. Positives 520,000, negatives
520,000, **1:1** (D002). Decoys are unobserved 8–12mers from proteins yielding at
least one observed peptide, length-matched to each participant's own profile. Their
sampling is **size-biased rather than uniform** over distinct sequences — mean
proteome multiplicity 1.47–1.85 against 1.06–1.10 for a uniform draw — which
shifts the composition floor by −0.0011 and the endpoint by +0.0007, so it is a
misstated property rather than a material effect (D062, L30). The deposit is established in the field; this
re-analysis is, to our knowledge, its first use for this question.

**Data splits.** 42 participants for cross-validation in 5 folds (9/9/8/8/8),
**10 participants held out**. No separate validation set: the CV folds serve
that role, and the held-out partition was **read once**. Rows: 840,000 CV,
200,000 held out. Length distribution is **identical between classes by
construction** (8–12 residues) and T06 asserts it; F15 plots the composition
and leakage figures.

**Redundancy between data splits.** The split is **participant-disjoint**, not
similarity-reduced. The sets are therefore independent *as donors* and **not**
independent *as sequences*: **15.988%** of held-out positives occur verbatim in
training, because the same peptide is seen in several donors. This is
measured, not assumed, and the realised figure **exceeds the 95th percentile of
2,000 random splits** (15.958%). A leak-free sensitivity arm removes the
15,988 exactly-overlapping rows (D003); **402 rows (0.479%) remain within one
substitution** of a training positive (L29). No similarity threshold was
applied, and the Discussion states why SpanSeq's machinery does not transfer to
8–12-mers.

**Availability of data.** Derived tables — `POSITIVES.csv`, `NEGATIVES.csv`,
`SPLIT.csv`, `TEST_LEAKFREE.csv` — ship in this repository under its licence,
with **exact splits included**, which is DOME's requirement. Raw payloads are
not redistributed; `DATA_SOURCES.md` records every source and SHA-256.
`data/external/PXD004023/units.json` is withheld pending the redistribution
position for that deposit (D054 §4) and is declared absent rather than omitted
silently.

## Optimization

**Algorithm.** 1-D convolutional neural network. **Not new**, and deliberately
so: §11 fixed an ordinary architecture before any data was read, because the
study measures what dataset construction costs, not what an architecture
achieves.

**Meta-predictions.** **Not applicable.** The model takes peptide sequence
only. No output of another predictor is an input, so the meta-predictor
independence question does not arise. The four external predictors are
compared against, never consumed.

**Data encoding.** Integers 1–20, **0 = pad**, centre-padded to length 12 so
both termini align; the trainer's selftest asserts the transform is lossless.
**Known defect** (the third of the construction faults reported in the Discussion; this is its mechanism). `IDX.get(ch, 0)` maps the non-standard residues B, X and Z to
**0, the padding token**. Only positives contain them, so **181 positive rows**
encode to a zero pattern that **no decoy of the same length produces** — 0 of
520,000 decoys show a non-canonical pattern. 22 of the 181 lie in the held-out
partition. Negligible in magnitude, exact in kind, and reported.

**Parameters.** E=16, C=32, k=3, p=0.0, selected from a 16-point grid by mean
validation average precision across the 5 folds. `selection.json` records the
criterion and the chosen point.

**Features.** No feature engineering and **no feature selection**: the input is
the encoded sequence. The question of selection on non-training data therefore
does not arise.

**Fitting.** Training rows (840,000) **greatly exceed** the parameter count of
this small CNN, so the over-fitting regime DOME asks about is not the binding
risk here. Over-fitting was controlled by early stopping on validation AP and
is visible in the per-fold curves; under-fitting is excluded by the model
clearing the composition floor on CV.

**Regularization.** Early stopping, patience 10, max 100 epochs, on validation
average precision. Dropout was in the grid and **selection chose p = 0.0** —
reported as selected, not as intended.

**Availability of configuration.** `results/model/selection.json`,
`final.json`, and the 25 checkpoints ship in the repository. Optimizer: Adam,
lr 1e-3, batch 512, BCE-with-logits. **L27 records that the environment that
produced the checkpoints is inferred, not recorded** — training ran on a Tesla
T4 under torch 2.11.0+cu130, which this environment cannot reproduce (D052).

## Model

**Interpretability.** **Black box.** No interpretation claim is made and no
motif attribution is offered. The study's claims are about measured
performance under stated constructions, which does not require the model to be
transparent.

**Output.** Binary classification: observed peptide against unobserved
expressed-proteome decoy, scored as a probability.

**Execution time.** Scoring the 200,000 held-out rows with all 25 checkpoints
takes **7.0 s** on CPU in the pinned environment, measured. Training is **not**
reproducible here: no GPU (D052). `results/compute/benchmark.json` records this
machine, and `benchmark_compute.py` is exempt from the regeneration gate
precisely because it measures the machine.

**Availability of software.** All code in `scripts/`, in this public
repository, under its stated licence, with all 396 tracked files hashed in
`freeze_manifest.json`. **No DOI yet** — Q1-017 open. No web server or
container; the pipeline is scripts plus `requirements.lock`.

## Evaluation

**Evaluation method.** 5-fold participant-disjoint cross-validation for
selection; a **single read** of the held-out 10 participants for the endpoint,
under a threshold fixed beforehand. Plus one **external cohort**, PXD004023,
for the platform-composition effect (D055).

**Performance measures.** Mean per-participant **average precision** (D008),
with the participant as the unit of analysis. AP is reported rather than AUROC
because its floor is the prevalence, which the leakage-free comparison changes
— the reason D057 exists. Per-participant values ship in `endpoint.json`.

**Comparison.** Against **four baselines**: the preregistered composition floor
(0.597), the prevalence floor, three published predictors on identical rows
(NetMHCpan 4.1, MHCflurry 2.0.0 and 2.3.0, MixMHCpred 3.0), and **a recurrence
lookup classifier that reads no sequence features at all**, which scores
**0.6426** — above the composition floor (D056, L28). DOME asks whether a
simpler baseline was compared; here one of them **beats the floor the study
preregistered**, and that is reported as a limitation rather than omitted.

**Confidence.** Cluster bootstrap over participants, B = 10,000, **nominal
99%**. Primary 0.7551 [0.7368, 0.7721]. **Nominal, not actual:** R6 measured
nominal-95% delivering 0.884–0.890 coverage at 10 units, so no 99% confidence
is claimed. The primary decision is a preregistered threshold rule, not a
significance test.

**Availability of evaluation.** Per-participant AP values, the four predictors'
per-peptide score tables (199,978 rows each), the 22 ambiguity-skipped rows,
every QC gate record and all nine figures ship in `results/`. The §18
predictor comparison is published **by written consent from DTU Health Tech**
(D051, L26), scoped to the average-precision comparison and the score table.

---

## Where this study fails DOME

- **Data, redundancy between splits.** DOME's requirement is independence
  between training and evaluation sets. This study's splits are independent by
  participant and **demonstrably not independent by sequence**. It reports the
  dependence rather than removing it.
- **Optimization, availability of configuration.** The training environment is
  inferred for the artifacts written before run records began (L27). The
  checkpoints are shipped and hashed, but "reproduce this in the original
  environment" has no precise referent.
- **Model, availability of software.** No DOI and no container.
- **Data, evidence of representativeness.** 10,000 peptides per participant is
  a cap against an observed universe of 2,658,972. Sufficiency is not claimed.
