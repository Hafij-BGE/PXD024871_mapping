# REPORT

Continuously updated report required by `PROJECT_PROMPT.md` §7. Every claim
below links to the analysis, artifact, or decision that supports it.

**State as of 2026-10-06:** no dataset has been retrieved. The only completed
analysis is a design-resolution study (run-001). Nothing here is an empirical
finding about PXD024871.

---

## Introduction

Class-I major histocompatibility complex molecules display short peptides,
typically eight to twelve residues, on the cell surface, where they are
available for inspection by cytotoxic T cells. Which peptides a given cell
displays depends on its MHC allotype: each allele binds a restricted set of
sequences, so the displayed repertoire differs between individuals. Mass
spectrometry of peptides eluted from immunoprecipitated complexes yields
direct observations of that repertoire, and such experiments are deposited
publicly in increasing numbers.

Predicting presentation from peptide sequence is an established task with
established tools. The question this experiment asks is narrower and more
specific: whether a deliberately simple convolutional network, trained on one
publicly deposited immunopeptidomics dataset, can distinguish observed
class-I-associated peptides from appropriately constructed controls, and whether
any signal it finds survives evaluation on biological units it never saw in
training.

**References in this report are deliberately absent.** No publication has been
retrieved or verified during this work, and the References section records that
rather than filling itself with citations from memory. Statements of background
above are at textbook level and are not attributed to any specific source.

### Why this question is harder than it looks

An experiment of this shape has several ways of producing a number that means
less than it appears to. The negative class is constructed rather than observed,
so its composition determines how much of any apparent performance reflects
discrimination rather than an artefact of how the controls were drawn. Peptides
recur across individuals, so splitting by individual does not by itself prevent
a model from being tested on sequences it has already seen. Instrument and
sample preparation leave signatures in which peptides are detected at all, so a
model held out on unseen individuals may be tested partly on unseen instruments.
And the quantity that bounds every claim is the number of independent
individuals, which in a dataset of this kind is small and fixed, however many
millions of peptides it contains.

Each of these is a known hazard in principle. What this work does is **measure
them in this dataset** before any model is fit, so that the resulting claim is
stated with its qualifications attached rather than defended afterwards.

### What this report is

**A design, preregistration and result report, in that order.** It documents the
retrieval and provenance mapping of the source submission, the construction and
freezing of an analysis dataset and an evaluation split, the diagnostics that
selected the negative controls and calibrated the statistical procedure, and the
decision rule fixed in advance for the primary hypothesis — and then, in R9 and
R10, what happened when that rule was applied once.

**Most of this report was written before any model existed, and none of it has
been rewritten since.** The preregistered decision rule, the pre-committed
interpretation table, and the four design estimates later checked against
outcomes all stand as written. R9 and R10 were appended; the Discussion marks
which pre-committed row applies rather than replacing the table.

This ordering is the point. Each of the hazards above was quantified before the
corresponding design choice was made: the negative construction was selected on a
composition diagnostic, the per-participant sample size on a precision curve, the
reporting interval on measured coverage, and the decision threshold on measured
power. Where a quantity could not be measured in advance, the handling was fixed
as a protocol so it could not be chosen once the answer was known.

The result of that ordering is a narrower question than the one originally
posed, with the narrowing documented rather than discovered later. The
Discussion sets out how much narrower, and the Limitations section states what
the study cannot claim — written before any model existed, and unchanged by what
the model turned out to do.

## Methods

All analyses to date are recorded in `RUN_LOG.md` (runs 001–012) with code
blob hashes, inputs, parameters and outputs. Every figure below is traceable to
a QC report in `results/qc/` or a results file in `results/`. **No model has
been fit.**

### Source data and retrieval

Two sources were retrieved from the PRIDE Archive: the submission file manifest
(504 records, obtained as six paginated requests — the API silently caps
`pageSize` at 100, so a single request returns an apparently complete 100-record
response) and the community-annotated sample metadata file (402 rows, 37
columns). A human reference proteome (UniProt release 2026_03, 20,652 sequences)
was retrieved for negative construction.

Of 504 deposited files, 503 carry a publisher checksum; the sole exception is
the metadata file itself, which is also the single evidence source for sample
class, participant identity and genotype. Its integrity rests on our own
SHA-256 plus agreement between its retrieved size and the manifest's declared
317,806 bytes. Every retrieval is recorded in `data/raw/*/provenance.jsonl` with
our own SHA-256 computed independently of any published hash
(`results/qc/QC_G1.md`).

### Provenance mapping

Five mappings were specified before execution under the governing project
prompt's eleven-field format (`METHODOLOGY.md`) and executed in run-003.
**Approximate matching is prohibited on every identifier join** (D016): in this
submission, acquisition filenames differ by one character between distinct runs
and participant identifiers by one digit between distinct individuals, so any
edit-distance threshold loose enough to repair a typo would also silently merge
distinct entities.

The file-to-metadata join is exact and complete: 402 acquisitions against 402
metadata rows, matched in both directions, zero rejects. Sample class was
assigned from a controlled vocabulary of the two distinct antibody-enrichment
annotations present, never inferred from filenames, giving 222 class-I and 180
class-II acquisitions. An independent metadata column recording the MHC protein
complex agreed on 402 of 402 rows with zero conflicts. Genotypes parsed without
a single nomenclature failure across all 52 class-I participants, yielding 46
distinct alleles; 38 participants carry a full six-allele complement and 14
fewer. **Incomplete genotypes were not imputed** (D012): from this metadata a
missing allele is indistinguishable between genuine homozygosity and incomplete
reporting.

The participant is the analysis unit (D011), with technical replicates and
fractions nested within it: 52 class-I participants over 222 acquisitions,
3–15 acquisitions each.

One specified mapping failed. Identification containers record their input
spectrum files under the original laboratory filenames, which share no
intersection with the deposited filenames — the files were renamed at
deposition, and the internal references additionally use a different participant
identifier scheme for which no cross-walk exists in the deposit. Run-level
attribution is therefore not recoverable by the specified method. The analysis
does not require it, because the unit is the participant and container stems
correspond one-to-one with all 52 metadata-derived participants, but attribution
consequently rests on a filename and carries reduced status
(`results/qc/QC_G3_pilot.md`).

### Peptide extraction

All 52 class-I identification containers (47.85 GiB) were retrieved, each
verified against its publisher SHA-1 before use, its peptide table extracted,
and the container deleted — peak working storage one container rather than the
whole set. Extraction refuses any container whose checksum is unverified: during
this work one transfer truncated at 77% and would otherwise have contributed a
silently incomplete peptide table.

The deposited search was already restricted to 8–12 residues. The union across
all participants is **2,658,972 unique peptides** (sum of per-participant counts
3,850,275; redundancy 1.45×), with 39,991–198,567 per participant and 9-mers the
modal length at 27.8%. **79.9% of the union occurs in exactly one participant.**
99.29% is at the highest reported confidence level, so confidence-based
re-filtering removes 0.7% and is not a meaningful purity control (D004).

### Dataset construction

**Positives.** 10,000 per participant, sampled stratified by length in
proportion to that participant's own length distribution, seed 20261006 (D024).
The cap was chosen from a precision curve, not a compute budget: the estimand's
variance decomposes into between-participant and within-participant terms over a
fixed 52 participants, and at 10,000 the within-participant term is already 15×
smaller than the between-participant term, so using all 2.66M peptides would
improve the interval by 0.16%. Because every participant holds at least 39,991
peptides the cap binds uniformly, which additionally equalises contribution
across participants that otherwise vary five-fold.

**Negatives.** Length-matched peptides drawn from proteins yielding at least one
observed peptide (20,152 of 20,652, 97.6%), excluding every observed sequence,
at a 1:1 ratio (D002). The construction was selected by a preregistered
diagnostic: the optimal linear classifier on amino-acid composition alone,
without positional information, separates reference-derived negatives from
positives at AUROC 0.6120 and these expressed-protein negatives at 0.6085, while
shuffled-positive decoys give exactly 0.5000 by construction. Shuffled decoys
were rejected as the primary set despite that perfect score, because shuffled
strings are not peptides any cell could present and a model separating real
fragments from them can succeed on sequence realism alone; they are retained as
a preregistered secondary control. **The resulting floor is not chance**: a
composition-only model achieves an average precision of 0.597 against the
primary negatives, and all performance is reported against that figure
(`results/qc/negative_diagnostic.json`).

The frozen dataset is 520,000 positives and 520,000 negatives over 52
participants, with checksums in `data/derived/FREEZE.json`. 53,054 positive rows
(10.20%) are sequences also positive in another participant; these are retained
rather than deduplicated, being the exposure the split must handle.

### Split

Ten participants were held out as a test partition, the remaining 42 divided
into five grouped folds for model selection, every partition stratified by
acquisition platform (D025). Two secondary splits were fixed before any result:
an allele-disjoint split holding out all 29 carriers of the most common allele,
and a cross-platform transfer analysis training on one instrument and evaluating
on the other in both directions.

**Participant-disjointness does not deliver sequence-disjointness.** Across
2,000 random ten-participant partitions, 14.59% of test positives also appear in
training (11.76–17.25%), because exposure compounds across 42 training
participants rather than remaining at the pairwise rate. The realised split
leaks 15.99%, near the top of that range; it was not re-drawn, as selecting a
split on its leakage would be selection on a property of the data. The 84,012
leakage-free test rows are written out and the primary metric is reported on
both partitions, the gap between them measuring the inflation directly (D003).

### Statistical analysis

The estimand is the mean per-participant average precision. Uncertainty is
assessed by cluster bootstrap resampling participants, which is what bounds the
claim: simulation established that bootstrap replicates are irrelevant across a
250-fold range while participant count is not (run-001). Nominal 95% intervals
were measured to achieve only 0.884–0.890 actual coverage at ten held-out
participants, so **all intervals are reported at nominal 99%**, which delivers
approximately 95% (run-012).

The preregistered decision rule rejects the null when the lower bound of a
nominal-99% interval exceeds **0.647** — the composition floor of 0.597 plus a
lift of 0.05 (D008). This rule has power 0.98 at a true AUROC of 0.75 and 0.42
at 0.70, with a false-positive rate of 0.000 when the truth lies at the floor.
The minimum reliably detectable effect is therefore a lift of about 0.14 average
precision; **failure to reject is not evidence of absent signal.**

Seeds are derived per purpose from a base of 20261006 by hashing, so unrelated
draws do not share a stream. Sensitivity analyses over seeds report every
replicate; selecting among them is prohibited (D010).

### Preregistration

The dataset, split, endpoint reference and decision rule are fixed at commit
`f7550f54`, with artifact checksums recorded in `PREREGISTRATION.md`, committed
at that commit. No tag was published: one was attempted and refused by the
remote, and the commit is the anchor instead. That
record establishes content integrity and ordering within the repository; it does
**not** provide independent third-party evidence of chronology, since it is
created by the repository owner (D009).

Sections 11, 12 and 13 — architecture, input representation and training
protocol — were found unfrozen while this section was being written, having been
carried past the freeze commit unlocked, and were frozen in response (D026). The
network is two convolutional blocks over a centre-padded length-12 encoding,
trained with a fixed 16-point hyperparameter grid selected on mean validation
average precision across the five folds. The preregistration is now complete:
any deviation requires a new decision entry and renders the affected claim
exploratory.

### Secondary analyses

Four were run after the endpoint, each preregistered in a decision entry before
its numbers existed, and each trained on units inside the primary test partition
— stated rather than worked around, since none serves §25.

**Cross-platform transfer** (D025, D028). Train on one instrument platform's
units, evaluate on the other's. The preregistered form alone confounds platform
with training-set size, so a matched control halves each platform by seed, trains
ten units from each half, and scores both models on both held-out halves. That
gives two contrasts: one holds the model fixed and moves the test platform, the
other holds the test units fixed and moves the training platform.

**Dominant-allele-held-out transfer** (D001, D029, D030). The frozen
`allele_disjoint_partition` holds out one allele rather than a disjoint set —
only 5 of 36 test alleles are absent from training, and 21.7% of a test unit's
repertoire — so it is reported as dominant-allele-held-out and a real effect
arrives attenuated roughly fivefold.

**Multi-allele test** (D031). Five alleles in the per-allele design, plus the one
allele pair whose mutually exclusive groups are both large enough, where both
arms are carrier-trained and a sign reversal between the two exclusive strata is
the signature. Non-carriage is required to be **locus-certain**: a unit counts as
a non-carrier only if it reports two alleles at that locus and neither is the
allele in question, because PARTIAL typing under-reports a locus.

**Three controls run on every comparison**, because each catches a distinct
alternative. An arm-specific composition-only LDA floor, fitted on that arm's own
training rows — the pooled floor misleads, since arm floors range 0.59–0.66. A
recurrence-matched control, equally recurrent and equally unseen but not
exclusive to one class. And a direct estimate of the training-set quality
difference on class-shared peptides, which caught a false positive at A\*01:01
that no symmetry argument would have.

**Every evaluation subset reports what each compared model had already seen in
training** (D030). This was added after a stratum turned out to be 97.93%
memorised by one arm and 0.00% by the other, making its effect a memorisation
measurement. A subset whose definition references one model's training units is
void until that fraction is shown equal across the models compared.

### Predictor comparison

Admission follows D006, fixed before any predictor ran: no predictor enters §18
until its training peptide list is retrieved and registered as an S6 source with
checksum and version, and overlap is measured by exact sequence match against
the frozen test partition — provenance is not a substitute.

Both MHCflurry release lines were admitted. The authoritative training list is
the one each **model bundle** ships per component, not the curated release the
line declares: release 2.3.0 pairs 2026 models with a 2023 curated file, so the
declared file would only have bounded the overlap below.

The comparison runs on rows naive to **both** systems (D033). D006's literal
"non-overlapping subset" removes only the predictor's 8–9% and would leave the
CNN's measured 15.99% in place — a selectively easier dataset, which §18 forbids
in those words. The predictor-naive-only and full-partition versions are
reported alongside. Peptides are scored against their own participant's recorded
alleles; 22 rows carrying ambiguity codes are excluded from both systems so the
rows stay identical.

### Software and environment

Phase A and dataset construction use only the Python standard library. The
design analyses use numpy 2.4.6 and scipy 1.17.1; the network uses torch 2.14.1.
Environments are recorded in `ENVIRONMENT.md`: `env-001` (4-core cloud
container, no GPU) for analysis, `env-002` (Colab, 2 cores) for extraction.
Measured training throughput for the benchmarked configuration is 122,648
peptides/second on `env-001`, from which the compute budget derives and to which
it does not port.

The selection grid and final fit ran on a Colab T4; every secondary analysis and
the endpoint read ran on `env-001` CPU. MHCflurry 2.3.13 and its TensorFlow
dependency live in a separate virtualenv, which is why scoring and comparing are
two scripts — neither environment carries the other's dependencies.

## Results

R1–R8 concern the dataset and the design. R9 reports the primary endpoint, read
once on 2026-10-07 under the rule fixed in D008 before any model existed; R10
reports the preregistered cross-platform transfer. Interpretation is deferred to
the Discussion; this section reports measurements.

### R1 — Provenance mapping

| Quantity | Value | Source |
|---|---|---|
| Deposited files | 504 (402 acquisitions, 101 identification containers, 1 metadata) | `QC_G1.md` |
| Acquisition ↔ metadata join | 402 ↔ 402, matched both directions, **0 rejects** | `QC_G1.md` |
| Class-I / class-II acquisitions | 222 / 180 | `QC_G2.md` |
| Independent class-column agreement | 402 / 402 rows, **0 conflicts** | `QC_G2.md` |
| Class-I participants | 52 (61 across the submission; 9 class-II only) | `QC_G3.md` |
| Acquisitions per participant | 3–15 (29 at three, 17 at five) | `QC_G3.md` |
| Distinct alleles | 46 across 52 participants | `UNIT_GENOTYPE.csv` |
| Genotype parse failures | **0** | `QC_G2.md` |
| Complete / partial typing | 38 / 14 | `QC_G2.md` |
| Acquisition platforms | 127 acquisitions on one, 95 on the other; participants split 25 / 27 | `QC_G3.md` |
| Participants spanning both platforms | **0** | `QC_G3.md` |

The allele-frequency distribution determines whether an allele-disjoint
evaluation is constructible. The most common allele occurs in 29 of 52
participants (56%), so holding out its carriers leaves 23 for training — costly
but feasible.

### R2 — The peptide universe

All 52 class-I containers retrieved and verified against publisher checksums
(52/52), extracted, and deleted.

| Quantity | Value |
|---|---|
| **Union, unique 8–12mers** | **2,658,972** |
| Sum of per-participant counts | 3,850,275 |
| Redundancy factor | 1.45× |
| Per participant | 39,991 – 198,567 (median 71,784) |
| Occurring in exactly one participant | 2,124,276 (**79.9%**) |
| Occurring in two or more | 534,696 (20.1%) |
| Highest confidence level | 99.29% of the union |

Length distribution: 8-mers 15.47%, 9-mers 27.80%, 10-mers 26.44%, 11-mers
18.67%, 12-mers 11.61%.

Accumulation had not saturated: Heaps' exponent over all 52 participants is
0.977, and the last participant added was 55% novel. A projection fitted to the
first five participants gave 1,547,364 — **41.8% below** the measured value.

Pairwise overlap between participants is 2.9–6.2%. Pairs sharing at least one
allele overlap a mean 4.8% against 4.0% for genotype-disjoint pairs — a ratio of
1.21, so overlap barely tracks shared alleles.

### R3 — Frozen dataset and split

| Quantity | Value |
|---|---|
| Positives / negatives | 520,000 / 520,000 (1:1) |
| Participants | 52 × 10,000 positives each |
| Distinct positive sequences | 466,946 |
| Positive rows shared with another participant | 53,054 (10.20%) |
| Source proteins for negatives | 20,152 of 20,652 (97.6%) yielding ≥1 observed peptide |
| Integrity checks | 6 / 6 pass |

Split: 10 participants held out (5 per platform), 42 in five grouped folds
(4 and 4–5 per platform per fold). Frozen at commit `f7550f54` with checksums in
`PREREGISTRATION.md`.

### R4 — Negative-control diagnostic

Optimal linear classifier on 20-dimensional amino-acid composition, no
positional information, held out:

| Candidate negative set | Composition-only AUROC | Composition divergence |
|---|---|---|
| Reference-derived, length-matched | 0.6120 | 10.05 pp |
| Shuffled positives | **0.5000** | 0.00 pp |
| **Expressed-protein, unobserved (selected)** | **0.6085** | 10.26 pp |

The selected set's composition-only separability corresponds to an average
precision of **0.597** at 1:1, which is the floor against which all performance
is reported.

### R5 — Leakage and confound audit

| Measurement | Value |
|---|---|
| Test positives also in training, 2,000 random splits | mean 14.59% (11.76 – 17.25%) |
| On the realised split | **15.99%** |
| Leakage-free test subset | 84,012 of 100,000 rows |
| Platform separability from composition alone | **AUROC 0.6451** |
| Control: random halves of participants | **0.5150** |
| Excess attributable to platform | **+0.1301** |

A visible mechanism in the length profile: 12-mers are 11.69% of one platform's
positives against 9.85% of the other.

### R6 — Design resolution

Simulation under a binormal model at the frozen conditions (10 held-out
participants, 1:1).

**Bootstrap replicates are irrelevant; participant count is not.** Increasing
replicates 250-fold (200 → 50,000) changes the interval half-width by less than
0.002; increasing participants from 10 to 26 narrows it 35%.

**Nominal intervals under-cover:**

| Nominal | Actual coverage |
|---|---|
| 95% | 0.884 – 0.890 |
| 97.5% | 0.918 – 0.928 |
| **99%** | **0.944 – 0.962** |

**Per-participant positives saturate early.** Within-participant sampling
variance falls to 0.066 of between-participant variance at a cap of 10,000; the
interval improves 0.16% between that cap and using all 2.66M peptides.

**Power at the preregistered rule** (reject when the nominal-99% lower bound
exceeds 0.647):

| True AUROC | True AP | Power |
|---|---|---|
| 0.70 | 0.6875 | 0.42 |
| 0.75 | 0.7390 | 0.98 |
| 0.80 | 0.7913 | 1.00 |

False-positive rate with the truth at the floor: 0.000.

The paired predictor comparison detects differences of roughly 0.05 average
precision at this participant count, against 0.14 for the absolute claim.

### R7 — Compute

Measured training throughput for the frozen architecture: **122,648
peptides/second** on four CPU cores without a GPU. The frozen design — 16
configurations × 5 folds plus a 25-run final fit, 105 runs — costs **24.7 hours**
at the 100-epoch worst case against a 96-hour budget, or roughly 10 hours with
typical early stopping.

### R8 — Not obtained

**Superseded.** This section recorded §18 as having no result because no
predictor's training-set membership list was obtainable, and the
allele-disjoint analysis as not run. Both have since been done: §18 in R13, the
allele analyses in R11 and R12. The original claim about obtainability was
wrong, and D006's outcome block records why — github.com's bare domain was
measured rather than its release assets, and each MHCflurry model bundle ships
its own training data. What remains genuinely not obtained is listed in the
Limitations section and in the gate table: the S4 acquisitions, NetMHCpan,
MixMHCpred, and sets A and B of the negative construction.

### R9 — Model selection and the primary endpoint

**Selection.** All 16 grid configurations completed over the 5 folds.
`{E:16, C:32, k:3, p:0.0}` was selected on mean validation average precision at
0.7525. **The grid is flat:** the spread between the best and worst
configuration is 0.0129, against a mean within-configuration fold spread of
0.0117. Selection is therefore not distinguishable from fold noise, and the
selected configuration should be read as *one of sixteen that perform alike*,
not as a tuned optimum. It is also the smallest configuration in the grid.

**Final fit.** 25 models, 5 folds × 5 seeds. Between-fold spread of mean
validation AP is 0.0132; seed spread within a fold averages 0.0024. Performance
is governed by *which participants are held out*, five times over, more than by
initialisation — which is what the run-001 variance decomposition predicted when
it put between-unit variance 15× above within-unit.

**Endpoint, read once.** 10 held-out participants, 200,000 rows, per-unit
average precision averaged across the 25 models (D027), nominal-99% cluster
bootstrap over participants (D008):

| Quantity | Value | CI99 | Per-unit range |
|---|---|---|---|
| **Primary — full test partition** | **0.7551** | [0.7368, 0.7721] | 0.7102–0.7911 |
| Sensitivity — leakage-free subset (D003) | 0.7056 | [0.6926, 0.7184] | 0.6796–0.7269 |
| Secondary — score-ensembled (D027) | 0.7651 | — | — |

**The null is rejected.** The lower bound 0.7368 exceeds the preregistered
threshold of 0.647 (floor 0.597 + 0.05). It is rejected again on the
leakage-free subset, whose lower bound 0.6926 also clears 0.647 — so the result
does not depend on the 15.99% of test positives that also appear in training.
Leakage inflates the primary by **+0.0495**, a real and measurable amount that
does not change the decision.

The ensembled figure is higher than the primary and is reported as the
*flattering* framing, which is why D027 made the per-model average primary
before the partition was read.

**Per-length decomposition** (`endpoint_by_length.json`, added for §20's
robustness requirement). The same 200,000 rows and the same 25 models, split by
peptide length; the pooled value reproduces at 0.7551 exactly. **Not a second
reading** — every length is reported, none is selected, and the primary decision
is fixed:

| Length | rows | mean per-unit AP | CI99 |
|---|---|---|---|
| 8-mer | 31,474 | 0.7649 | [0.7393, 0.7914] |
| 9-mer | 64,954 | 0.7660 | [0.7379, 0.7890] |
| 10-mer | 50,922 | 0.7297 | [0.7029, 0.7565] |
| 11-mer | 33,244 | 0.7421 | [0.7176, 0.7627] |
| 12-mer | 19,406 | 0.7850 | [0.7582, 0.8047] |

Spread 0.0553, and **every length's lower bound clears the 0.647 threshold**:
the result is not carried by one length. One caveat in the unflattering
direction: the best length is the 12-mer, and 12-mers are also the most
platform-discriminative length D025 found (11.69% of LTQ positives against 9.85%
of Lumos). R10 bounds how much of the signal that can be, but the coincidence is
recorded rather than omitted.

### R10 — Cross-platform transfer

D025 preregistered this before training; D028 added a matched within-platform
control before the run and before any of its numbers were visible. Every floor
below is a composition-only LDA fitted on that arm's own training rows and
scored on its own test rows, because the pooled 0.597 is not the composition
separability of a cross-platform test set. Full detail in
`results/qc/QC_G12_transfer.md`.

| Arm | train | test | mean AP | CI99 | own floor | lift |
|---|---|---|---|---|---|---|
| LTQ → Lumos (D025) | 20 LTQ | 27 Lumos | 0.6959 | [0.6805, 0.7113] | 0.5917 | +0.1042 |
| Lumos → LTQ (D025) | 22 Lumos | 25 LTQ | 0.7108 | [0.6993, 0.7221] | 0.6093 | +0.1015 |
| within LTQ (D028) | 10 LTQ | 12 LTQ | 0.7481 | [0.7244, 0.7743] | 0.6648 | +0.0833 |
| across → Lumos (D028) | 10 LTQ | 13 Lumos | 0.6879 | [0.6608, 0.7142] | 0.5919 | +0.0961 |
| within Lumos (D028) | 10 Lumos | 13 Lumos | 0.7379 | [0.7244, 0.7499] | 0.6158 | +0.1221 |
| across → LTQ (D028) | 10 Lumos | 12 LTQ | 0.6965 | [0.6791, 0.7140] | 0.6102 | +0.0863 |

**It does not collapse.** Both preregistered arms clear the D008 threshold —
lower bounds 0.6805 and 0.6993 against 0.647, and against their own
arm-specific thresholds of 0.6417 and 0.6593. A model that has never seen a run
from the target instrument ranks peptides from unseen participants on that
instrument 0.10 AP above what composition alone achieves on the same rows.

**A platform effect is nonetheless there.** Two contrasts, built so that one
holds the model constant while the test platform moves and the other holds the
test units constant while the training platform moves:

| Contrast | difference | CI99 | units degraded |
|---|---|---|---|
| same model, test platform moves (LTQ-trained) | +0.0601 | [+0.0243, +0.0979] | — |
| same model, test platform moves (Lumos-trained) | +0.0414 | [+0.0200, +0.0631] | — |
| same test units, training platform moves (LTQ half) | +0.0516 | [+0.0261, +0.0745] | 10 / 12 |
| same test units, training platform moves (Lumos half) | +0.0500 | [+0.0295, +0.0741] | 13 / 13 |

Four estimates from two designs, agreeing to within 0.01, none of the intervals
containing zero: training on the other platform costs **0.04–0.06 AP**. A cost,
not a collapse.

**Post-hoc.** Paired per unit against the penalty a composition-only linear
model pays on the same units, the CNN's cross-platform penalty is
indistinguishable from the compositional one on the LTQ half (excess −0.0030,
CI99 [−0.0137, +0.0073], 5 of 12 units positive) and exceeds it on the Lumos
half (+0.0261, CI99 [+0.0176, +0.0349], 13 of 13). The asymmetry is reported as
a diagnostic that generated a hypothesis — D025 records that 12-mers are 11.69%
of LTQ positives against 9.85% of Lumos, and length is positional rather than
compositional — not as a test of one.

### R11 — Dominant-allele-held-out transfer

D001 preregistered an allele-disjoint secondary split. Measured before running
it (D029), the split is **not** allele-disjoint: the 29-unit test partition
carries 36 alleles and only 5 are absent from the 23-unit training partition,
23 of 29 test units have exactly one unseen allele, and the mean unseen
fraction is **21.7%**. It is a dominant-allele-held-out split, which is how it
is reported, and a real effect arrives attenuated roughly fivefold. Full detail
in `results/qc/QC_G12_allele.md`.

**The preregistered arm.** Train on the non-carriers of HLA-A\*02:01, test on
the 29 carriers:

| P_AD | mean per-unit AP | CI99 | own floor | lift |
|---|---|---|---|---|
| all rows | 0.7422 | [0.7302, 0.7534] | 0.6371 | +0.1051 |
| leakage-free against its own training units | 0.7210 | [0.7103, 0.7308] | 0.6147 | +0.1064 |

That lift is indistinguishable from the cross-platform arms' +0.1015 and
+0.1042. **A model that has never seen a unit carrying the cohort's most common
class-I allele performs on carriers of it as well as it does anywhere else.**

**The matched contrasts (D029), corrected for memorisation (D030).** Every row
set excludes positives either arm saw in training, so the two models are equally
naive to every sequence scored:

| Contrast I — 14 held-out carriers | paired difference | CI99 | units positive |
|---|---|---|---|
| all rows | +0.0072 | [−0.0015, +0.0162] | 9 / 14 |
| carrier-**exclusive** stratum | **+0.0335** | [+0.0236, +0.0438] | **14 / 14** |
| recurrence-matched control | +0.0056 | [−0.0137, +0.0279] | 8 / 14 |

| Contrast II — 8 held-out non-carriers | paired difference | CI99 | units positive |
|---|---|---|---|
| all rows | +0.0000 | [−0.0051, +0.0078] | 3 / 8 |
| non-carrier-exclusive stratum | −0.0131 | [−0.0287, +0.0040] | 2 / 8 |
| recurrence-matched control | +0.0065 | [−0.0296, +0.0507] | 3 / 8 |

The carrier-exclusive effect is not recurrence — paired
difference-of-differences against the recurrence-matched control on the same 14
units is +0.0279, CI99 [+0.0067, +0.0472] — and not one training set being
better, which is measured directly on class-shared peptides across 22 held-out
units at **+0.0005, CI99 [−0.0081, +0.0092]**.

**The verdict is nonetheless inconclusive, by the rule D029 fixed in advance.**
That rule read opposite contrast signs as "one training set is simply better",
and the signs are opposite. The premise is measurably false here, which is
recorded but does not convert a failed preregistered test into a passed one.
D029's defect was assuming the two groups are symmetric: the 29 carriers share
A\*02:01 while the 23 non-carriers share only its absence and span 41 alleles,
so contrast II is a weak replication test by construction. The symmetric test
that would settle it — repeating the design on HLA-C\*07:02 (24 units) and
HLA-A\*01:01 (17 units) — is named and deliberately not run, because adding arms
after a preregistered test fails is how a negative result becomes a positive one.

**One result in this section is void and kept anyway.** D029's original stratum
was defined as "observed in M_AM's training pool and absent from M_AD's", so
M_AM had trained on 97.93% of its rows and M_AD on 0.00%. The +0.0660 it
produced was memorisation and is the largest number the run produced. It stays
in `allele.json` with D030 pointing at it. It is the second occurrence of one
failure mode — the first `TEST_LEAKFREE` mask selected a subset with no
negatives and returned 1.0000 — and both times the broken version gave the most
flattering answer available, which is the argument for the standing check D030
adds.

### R12 — Multi-allele test

`QC_G12_allele.md` §4 named the test that would settle D029, and it was run on
request. D031 preregistered it. The point is Part B: **HLA-A\*02:01 and
HLA-C\*07:02 are the only pair whose mutually exclusive groups are both large
enough, and both of its arms are carrier-trained** — each for its own allele —
so neither group is the "defined by an absence" group that made D029's contrast
II uninformative. A sign reversal between the two exclusive strata was fixed in
advance as the signature. Detail in `results/qc/QC_G12_multi_allele.md`.

**Part B.** `A*02:01-trained − C*07:02-trained`, paired per unit, adjusted by
the neutral training-set difference measured on class-shared peptides:

| Row set | raw | neutral δ | recurrence control | **adjusted** | CI99 | units |
|---|---|---|---|---|---|---|
| A\*02:01-exclusive | +0.0463 | −0.0013 | +0.0052 | **+0.0476** | **[+0.0314, +0.0626]** | **9 / 9** |
| C\*07:02-exclusive | −0.0087 | −0.0038 | −0.0088 | −0.0049 | [−0.0366, +0.0298] | 3 / 6 |

**The sign reverses.** On the A\*02:01 side the effect survives every
alternative, each measured at zero on the same units: memorisation 0.00% by
construction, training-set quality −0.0013, recurrence +0.0052. On the
C\*07:02 side nothing is demonstrated — correct sign, interval containing zero,
6 units, 542 stratum sequences.

**Part A — replication across five alleles.** `carrier-trained −
non-carrier-trained` on each allele's exclusive stratum, adjusted by that
allele's own neutral δ:

| Allele | test units | exclusive | neutral δ | **excl − δ** | CI99 | units |
|---|---|---|---|---|---|---|
| A\*02:01 | 19 | +0.0278 | −0.0059 | **+0.0337** | **[+0.0252, +0.0421]** | **19/19** |
| C\*07:02 | 14 | +0.0068 | −0.0091 | **+0.0160** | **[+0.0048, +0.0269]** | 12/14 |
| A\*01:01 | 7 | +0.0229 | **+0.0146** | +0.0083 | [−0.0100, +0.0226] | 5/7 |
| A\*24:02 | 6 | +0.0408 | −0.0185 | **+0.0592** | **[+0.0432, +0.0732]** | **6/6** |
| B\*07:02 | 5 | +0.0415 | +0.0091 | +0.0325 | [−0.0087, +0.0722] | 4/5 |

All five positive; three exclude zero after adjustment, four against the
recurrence control. No joint p-value: the five splits share units, so these are
correlated replications.

**The neutral estimate earned its place on A\*01:01.** Raw +0.0229 would have
read as a fourth replication. Its neutral δ is +0.0146, CI99 [+0.0010,
+0.0270] — for that split the carrier-trained arm is simply the better model on
peptides where neither arm is matched — and only +0.0083 survives, with an
interval containing zero. This is the confound D029's sign rule tried to catch
by symmetry and could not; here it is caught by direct measurement, in one split
out of five.

**Both designs rank A\*02:01 above C\*07:02** (+0.0337 / +0.0160 in Part A,
+0.0476 / −0.0049 in Part B) — different training sets, different test units,
different comparators. A coherence check the design did not have to pass.

**What this establishes.** The model learns sequence features linked to donor
genotype, and for HLA-A\*02:01 that is demonstrated allele-specifically on a
symmetric design. **What it does not.** The same for HLA-C\*07:02 or HLA-C
generally; the identity of the restricting allele, since no deconvolution was
done and linkage is uncontrolled; and anything about whether the primary
endpoint's +0.158 lift is presentation biology — the allele effect is a few
hundredths of average precision on strata comprising 0.5–5% of each ligandome,
and every confound the platforms and allele groups *share* stands untouched.

**G13 stays held.** Three of D031's four release conditions are met. The fourth
required a nominal-99% interval from a 6-unit arm, which D031's own table shows
was close to unattainable — the same family of error as D029's symmetry
assumption, which is to say a reading rule whose design cannot supply what the
rule demands. **D032 proposes the narrowing and leaves it to the project owner**,
with the exact §20 wording it would license, because the criterion is mine and
relaxing it in order to pass it is self-serving by construction. §20 stays
unwritten meanwhile, and nothing downstream is blocked: §25 is read and closed.

### R13 — Comparison with existing predictors (§18)

D006 fixed the handling before any predictor was run; D033 executed it. Both
MHCflurry release lines were admitted as quantified `OVERLAPPING`, their
training lists taken from the model bundles themselves and registered as S6
sources with sha256. Detail in `results/qc/QC_G11.md`.

| | MHCflurry 2.0.0 | MHCflurry 2.3.0 |
|---|---|---|
| training peptides | 605,189 | 666,025 |
| overlap with test positives | 8.29% | 9.11% |
| overlap with test negatives | 1.20% | 1.16% |
| positive : negative bias | 6.9 : 1 | 7.9 : 1 |

**D006's central argument was confirmed by measurement.** The 2.0.0 models
predate this deposit's 2021-09 publication by fifteen months and name it
nowhere — and 8.29% of this test partition's positives are in their training
data regardless, arriving through other studies. On a date argument that line
would have been called clean, and the comparison would have carried an 8%
contamination nobody had counted.

**The comparison**, on rows naive to both systems — removing only the
predictor's overlap would leave the CNN's measured 15.99% in place and hand it a
selectively easier dataset, which §18 forbids in those words:

| Row set | rows | prevalence | CNN | MF 2.0.0 | MF 2.3.0 | CNN − 2.0.0 | CNN − 2.3.0 |
|---|---|---|---|---|---|---|---|
| **mutually naive (primary)** | 175,524 | 0.440 | **0.6859** | 0.5481 | 0.5519 | **+0.1378** | **+0.1340** |
| predictor-naive only | 187,764 | 0.477 | 0.7285 | 0.5892 | 0.5938 | +0.1393 | +0.1347 |
| full partition | 199,978 | 0.500 | 0.7551 | 0.6629 | 0.6673 | +0.0922 | +0.0877 |

Primary intervals: CI99 [+0.1151, +0.1583] and [+0.1126, +0.1505], **10 of 10
participants each**. The advantage is largest where contamination is smallest,
so it is not produced by memorisation — and the full-partition gap is narrower
because MHCflurry gains more from its own overlap (0.548 → 0.663) than the CNN
does from its (0.686 → 0.755). Average precision depends on prevalence, which
the subsetting moves from 0.440 to 0.500, so absolute values compare only within
a row set. The full-partition CNN figure reproduces the endpoint at 0.7551.

**What this does not establish, and the numbers that say so.** MHCflurry is
being asked a different question: it predicts whether a peptide *can* be
presented, and our label records whether it *was observed*. **11.78% of set-C
negatives are ranked strong presenters** (percentile ≤ 2) and 9.11% have
predicted affinity ≤ 500 nM. Each is counted as the predictor's error, and some
are the predictor being right about a peptide that simply went undetected. The
CNN also trained on 42 participants of this cohort — same laboratory, same two
instruments, same negative construction, whose instrument component R10 put at
0.04–0.06 AP — while MHCflurry never saw it. **A model trained on the task,
distribution and technical artefacts of the test set beating one that was not is
close to tautological.** §18 shows that the CNN adds information for this task
on this cohort. It does not show that it is a better model of HLA presentation,
and should not be cited as if it did.

**Not promoted.** D014 made promotion conditional on every admitted predictor
being clean or quantified-overlapping, which is now true; D014 equally bars a
switch after seeing results. §25 was read and closed before any predictor score
existed, so §18 stays secondary.

**One incidental finding.** MHCflurry's refusal of a peptide containing `X`
surfaced that the frozen positives hold **181 rows (0.035%) with ambiguity
codes** — X, B (Asx), Z (Glx) — and that the CNN's encoder maps an unknown
character to the **pad token**, so those peptides were encoded with internal pads
rather than rejected. 22 are in the test partition, 0.011% of its rows, so the
endpoint is unaffected at any decimal that matters. The defect is the encoder's
silent fallback and a selftest covering only standard residues — the same shape
as the bug that once deleted the middle of every long peptide, an encoder
accepting input it should have refused.

## Discussion

**Most of this section discusses the design, not the hypothesis**, and was
written before any model existed. The subsection on the pre-committed
interpretation table is where the endpoint and the transfer result are read, and
it is the only part written after them. The design discussion is kept first and
unchanged, because what question this dataset can answer — and how much narrower
that is than the question asked — bounds what any result can mean.

### The answerable question is substantially narrower than the proposed one

The proposal asked whether a sequence CNN can distinguish observed HLA class-I
peptides from appropriate controls and whether the signal generalizes to unseen
biological units. Each clause has since acquired a measured qualification.

*Distinguish from controls* now means distinguish from a baseline of 0.597
average precision, because a linear model on amino-acid composition alone
reaches that against the chosen negatives. *Generalizes to unseen units* is
confounded with generalizing across acquisition platforms, at a magnitude large
enough that a trivial model separates the platforms at 0.645. And the primary
figure will include 15.99% of test peptides seen verbatim during training,
because participant-disjoint splitting does not deliver sequence-disjointness in
a dataset where repertoires overlap.

None of this was apparent from the proposal, and none of it is a defect
introduced by the analysis. These are properties of the data that the design
work surfaced. The honest summary is that the study can answer a real question,
but a more qualified one than it set out to ask.

**Written before the model ran; here is how each qualification resolved.** The
0.597 floor held and the endpoint cleared it by 0.158. The platform confound
turned out to cost 0.04–0.06 AP rather than to dominate, so "generalizes to
unseen units" survives the instrument but is not free of it (R10). The 15.99%
leakage inflated the primary by 0.0495 and the leakage-free subset rejected the
null on its own (R9). Every qualification was real and none was fatal — which is
the outcome that the qualifications being *measured first* made legible.

### The most consequential finding so far is not about the model

It is that **the acquisition instrument is learnable from the peptide sequences
themselves**. Two platforms, no participant spanning both, and a composition-only
classifier separating them at AUROC 0.6451 against a 0.5150 control that
compares random halves of participants. Between-participant variation
contributes almost nothing; the platform contributes a third of the distance to
perfect separation.

This matters beyond the present experiment. Any analysis of this dataset that
holds out participants — and that is the standard design — inherits the same
confound, whether or not its authors measure it. The finding belongs to the
dataset, not to this study, and it would be worth reporting even if the CNN work
were abandoned.

### Interpretation was pre-committed, and the pre-commitment is now cashed

The table below was written before any model existed, mapping the proposal's
§21 outcomes onto the measured design so that the reading of each was fixed in
advance rather than negotiated afterwards. **It is left exactly as written.**
The row that applies is marked, and the resolution follows it.

| Result | Reading |
|---|---|
| **← APPLIES.** Rejects the null, holds within platform **and** across platform | The strongest reading available: sequence carries signal that survives both unseen participants and unseen instrument conditions. Still bounded to one disease, one tissue, one laboratory |
| Rejects, but collapses in cross-platform transfer | The signal is substantially instrument, not presentation. §25 would not be supportable as stated |
| Rejects on the full test partition but not on the leakage-free subset | Memorisation of the 15.99% overlap, not generalization |
| Fails to reject | **Not** evidence of absent signal. Power is 0.42 at AUROC 0.70, so a real effect below a lift of ~0.14 is more likely to be missed than found |
| Very high performance with any leakage or control check failing | Not interpretable biologically until resolved, per proposal §21 Outcome E |

**The first row is the one that applies, and it is the only one that does.** The
null is rejected on the full test partition (0.7551, lower bound 0.7368 against
a threshold of 0.647). It is rejected again on the leakage-free subset (0.7056,
lower bound 0.6926), so the third row — memorisation of the 15.99% overlap — is
excluded; leakage inflates the estimate by 0.0495 without carrying it. Both
preregistered cross-platform arms clear the threshold, so the second row — a
collapse across platforms, read in advance as *"the signal is substantially
instrument, not presentation"* — **does not apply**. No leakage or control check
failed, so the fifth row does not apply, and the fourth is moot.

That is the strongest reading the design permits, and it is worth being exact
about how strong that is. Three things are now established. Sequence carries
information that separates observed from unobserved peptides beyond amino-acid
composition. That information survives being tested on participants the model
never saw. It survives being tested on an instrument the model never saw, at a
measured cost of 0.04–0.06 AP, which is a cost and not a collapse.

Three things are not. The lift over the composition floor is 0.158 on the
primary and 0.09–0.10 in transfer — real, bounded, and nowhere near the
separation that would follow from a model of presentation itself; the first row's
own text already said "still bounded to one disease, one tissue, one
laboratory." Ruling out an instrument-specific signature does not rule out any
confound the two instruments **share**: source-protein abundance, proteolytic
and detectability bias common to both, and the set-C negative construction,
whose composition alone reaches 0.6085 AUROC against positives. And the
allele-disjoint analysis (D001) has not been run, so nothing here yet connects
the signal to allele-specific binding — which is the specific biological claim
§20 would want to make. **§20 should not be written as biology until D001's
analysis has run.**

The pre-commitment did the work it was supposed to do. The second row was the
live risk: D025's own evidence put platform at 0.6451 composition-only AUROC
against a 0.5150 control, which is a third of the way to perfect separation from
frequencies alone, and a disappointing transfer number would have been easy to
reinterpret after the fact. Because the reading was fixed first, the favourable
outcome is as constrained as an unfavourable one would have been: the second row
does not apply, and the first row's limiting clause applies in full.

### §20 — the biological reading, and its exact boundary

G13 was held through R10, R11 and R12, and released on 2026-10-07 when the
project owner accepted D032's narrowing of a release criterion that required
significance from a 6-unit arm. §20 is written to D032's wording verbatim:

> The model learns sequence features linked to donor genotype. For HLA-A\*02:01
> this is demonstrated allele-specifically: a model trained on carriers ranks
> peptides exclusive to carriers above a model trained on carriers of a
> different allele, on held-out participants, by 0.048 average precision
> (nominal-99% CI 0.031–0.063, 9 of 9 units), with memorisation, peptide
> recurrence and training-set quality each measured at zero on the same units.
> The direction reproduces across five alleles. It is not demonstrated for
> HLA-C\*07:02. The effect is a few hundredths of average precision on strata
> comprising 0.5–5% of each ligandome.

**And the boundary, carried from D032 so it cannot widen by paraphrase.** §20
does not state that the primary endpoint's lift is presentation biology; nor
that the restricting allele is identified, since no deconvolution was done and
linkage is uncontrolled; nor anything generalizing beyond this cohort, disease,
tissue and laboratory; nor anything about HLA-C.

§20 required that the alternatives to a biological reading be excluded
explicitly. Each was, by measurement rather than argument: memorisation by the
leakage-free endpoint and by a zero seen-fraction on all 21 multi-allele row
sets; instrument by the cross-platform transfer, which does not collapse;
training-set quality by a direct neutral estimate in every comparison, which
caught a false positive at A\*01:01 that would otherwise have counted as a
replication; peptide recurrence by a recurrence-matched control; composition by
an arm-specific floor on every single arm. Robustness across lengths is
reported above. Robustness across negative-control designs is **structurally
unavailable** — the dataset was frozen with set C alone — and is recorded as a
permanent limitation of the frozen design rather than as work outstanding.

**What the released gate is worth.** The claim is narrow and the number is
small: a few hundredths of average precision on a few percent of each
ligandome. What makes it worth stating is not its size but that it is the one
result in this project where a specific biological mechanism was isolated from
every alternative the design could measure. The primary endpoint's 0.158 lift
remains, as the Limitations section says it would, a measurement whose
biological content is bounded above by the confounds no split in this dataset
can break.

### What the design work suggests about design work

Four estimates made before measurement were checked against the outcome, and
the pattern is informative. The eligible-peptide count was projected 41.8% low.
The claim that ligandomes overlap heavily between participants sharing alleles —
which motivated treating cross-split leakage as a serious hazard — was wrong in
the reassuring direction: overlap is 20.1% and barely tracks shared alleles. The
conclusion that no GPU was needed was true at the dataset size assumed and false
at the size the data actually yields. The compute budget was consequently wrong
twice, both times in the optimistic direction.

The errors ran in both directions, which is the argument for measuring before
deciding rather than against it. Each was caught because the estimate was
written down in a form that could later be compared with an outcome; an estimate
that is never recorded cannot be found wrong, and the design would simply have
inherited it.

### What would strengthen the study

**External replication is the largest gap.** This is one submission, one
laboratory, one disease, one tissue. A second dataset with a different
instrument distribution would do more than any analytic refinement here: it
would break the platform confound that no split over these participants can
touch.

**Deeper sampling would settle the undersampling question.** Whether low
cross-participant overlap reflects distinct repertoires or shallow sampling of a
far larger presented space changes what "unseen participant" generalization
means. The testable signature is that overlap should rise with per-participant
depth, which this dataset cannot provide.

**The comparison with existing predictors remains the better-powered question.**
Simulation showed the paired comparison detects differences of about 0.05
average precision where the absolute claim requires 0.14. It was nonetheless
kept secondary, because its fairness depends on training-set overlap that may
not be verifiable — a well-specified weaker claim being preferable to a
better-powered one resting on an unchecked premise. If the comparison predictors'
training data proves inspectable, that ordering should be revisited, and the
condition for doing so is fixed in advance.

**It proved inspectable, and the ordering was not revisited.** Each MHCflurry
model bundle ships its own training data, so both lines were admitted as
quantified `OVERLAPPING` and D014's promotion condition is now met (R13). D014
equally bars a switch after seeing results, and §25 was read and closed before
any predictor score existed. The better-powered question stays secondary. The
paragraph above is left as written because it set the condition, and the point
of setting a condition in advance is that meeting it does not by itself license
the change.

## Limitations

Grouped by what they prevent the study from claiming. Those marked **measured**
have a magnitude in `results/`; the rest are structural.

### Limitations that bound the primary claim

**The instrument confound is total and cannot be removed — measured.** Two
acquisition platforms partition the 52 participants 25/27 with **zero overlap**:
no participant was run on both. No split over participants can therefore
separate participant effects from platform effects. Worse, the peptides
themselves carry a platform signature: a linear model on amino-acid composition
alone separates the two platforms at AUROC **0.6451**, against **0.5150** for a
control comparing random halves of participants. Generic between-participant
variation is near-nothing; platform is a third of the way to perfect separation.
A result on held-out participants is therefore a **joint** statement about
generalizing to unseen individuals and to unseen instrument conditions, and §25
cannot be worded as though it were about biology alone. Stratification bounds
the artefact; it does not remove it (D005, D025, `QC_G5.md`).

**Participant-disjointness does not deliver sequence-disjointness — measured.**
On the realised split, **15.99%** of test positives appear verbatim in training;
across 2,000 random splits the range is 11.76–17.25%. Exposure compounds across
42 training participants rather than staying at the pairwise rate. The
leakage-free subset (84,012 of 100,000 rows) is reported alongside, and the gap
between the two is the inflation — but the primary figure is the inflated one,
and must be read as such (D003).

**The floor is not chance — measured.** A composition-only linear model achieves
average precision **0.597** against the primary negatives. Roughly a fifth of
the distance from chance to a perfect score is available before the network
learns anything about sequence structure. Every reported figure is relative to
0.597, not 0.5 (D002).

**The study is underpowered for a modest effect — measured.** At the
preregistered decision rule, power is **0.42** at a true AUROC of 0.70 and 0.98
at 0.75. The minimum reliably detectable effect is a lift of about **0.14**
average precision. **Failure to reject is not evidence of absent signal**: it is
equally consistent with a real effect below the detectable range. This follows
from 10 held-out participants, which the data fixes and no analytic choice can
improve (D008).

*As it happened the observed lift was 0.158, just above the reliably detectable
range, so this limitation did not bite on the primary endpoint.* It bites hard
everywhere else: it is why the 6-unit arm in D031 could not satisfy the release
criterion D031 itself set, and why the allele effect at HLA-C\*07:02 is
undetermined rather than absent. **Having enough power once is not having
enough power.**

**Nominal intervals under-cover — measured.** Nominal 95% cluster-bootstrap
intervals achieve 0.884–0.890 actual coverage at this participant count.
Reporting is at nominal 99% to deliver approximately 95%; any figure quoted at
nominal 95% elsewhere would overstate precision by that margin.

### Limitations of the data itself

**Negative labels are not evidence of non-presentation — now measured, from
outside this project.** Negatives are peptides not observed, and non-observation
conflates genuine absence with detection limits. The repertoires are deeply
undersampled — redundancy across participants is 1.45× and the 52nd participant
added was still 55% novel — so the negative class is contaminated at an unknown
rate. This biases measured performance **downward** and is inherent to any
construction built on absence.

The rate is no longer entirely unknown. An independently trained presentation
predictor ranks **11.78% of the 100,000 test negatives as strong presenters**
(percentile ≤ 2) and gives **9.11%** a predicted affinity ≤ 500 nM (R13). Roughly
one negative in nine looks presentable to a model that never saw this cohort.
That is not a count of mislabelled rows — a presentable peptide may still
genuinely not be presented — but it is the first external bound on the
contamination, and it sets the direction: **every performance figure in this
report, the endpoint included, is depressed by it.**

**Low cross-participant overlap may be sampling, not biology.** Only 20.1% of
the union occurs in more than one participant, and overlap barely tracks shared
alleles (4.8% for allele-sharing pairs against 4.0% for disjoint pairs). The
parsimonious reading is depth: roughly 16,500 peptides observed per acquisition
from a far larger presented space, so even identical repertoires would overlap
little by chance. If that is right, "generalizes to an unseen participant" partly
tests generalization across *samples of* a repertoire rather than across
repertoires. The data cannot settle this; the testable signature is that overlap
should rise with per-participant depth.

**The cohort is uniform and narrow.** All 222 class-I acquisitions are from one
disease and one tissue; age and sex are recorded as unavailable for every row.
No covariate is available for confound modelling, and no claim extends beyond
this single clinical context. This is one submission from one laboratory: there
is no external replication anywhere in this design.

**The depositor's identification pipeline is inherited and unaudited.** The
acquisition files were deliberately not retrieved, so search parameters and
error-rate control are taken as given. Positive-set purity is capped at whatever
that pipeline achieved, and the expected lever — confidence-based re-filtering —
proved a no-op, removing 0.7% of the union.

**The single most load-bearing input has no publisher checksum.** 503 of 504
deposited files carry one; the exception is the metadata file, which is the sole
evidence for sample class, participant identity and genotype. Its integrity
rests on our own hash plus agreement with a declared size.

**Run-level attribution was not recoverable.** Container-internal references use
original laboratory filenames with no intersection with the deposited names, and
a different participant identifier scheme with no cross-walk in the deposit.
Attribution rests on container filenames, corroborated one-to-one against the
52 metadata participants but not independently verifiable. A misnamed container
at deposition would be undetectable from inside this pipeline.

**Fourteen of 52 participants are incompletely typed, and what that means was
characterised only late.** D012 recorded the count; D031 found the mechanism.
Each of those units reports **one** allele at one or two loci instead of two,
which makes homozygosity and an untyped second allele indistinguishable in the
source metadata. A unit reporting one HLA-A allele that is not A\*02:01 may
still carry it. Non-carriage is therefore certain only where the locus is fully
typed, and **2 of the 23 units used as A\*02:01 non-carriers in D001 and D029
are not certain** — 8.7% contamination, in the direction that weakens an allele
effect rather than manufacturing one. The multi-allele test requires
locus-certainty throughout; the two earlier analyses did not, and are reported
with that caveat rather than rerun.

The allele-disjoint secondary split is also costly: holding out the 29 carriers
of the most common allele leaves 23 for training.

**The positives contain 181 rows with amino-acid ambiguity codes, and the
encoder accepted them silently.** X, B (Asx) and Z (Glx) appear in 0.035% of
frozen positives and no negatives. The CNN's encoder maps an unknown character
to the **pad token**, so those peptides were encoded with internal pads rather
than rejected or flagged, and the selftest covers only standard residues. 22 are
in the test partition — 0.011% of its rows — so the endpoint is unaffected at any
decimal that matters. It was found only because MHCflurry refused one of them.
The defect is the same shape as the encoder bug that once discarded the middle of
every peptide longer than eight residues: input accepted that should have been
refused.

### Limitations that bound the secondary claims

**The allele result covers one allele.** HLA-A\*02:01 is demonstrated
allele-specifically on a symmetric design; HLA-C\*07:02 is not, and HLA-C is
untested as a locus. The symmetric test **cannot be replicated in this cohort** —
no second allele pair has ≥14 units on both sides — so strengthening it requires
a second cohort. The effect is also small in absolute terms: a few hundredths of
average precision on strata comprising 0.5–5% of each ligandome. And
"A\*02:01-exclusive" means exclusive to *carriers* of A\*02:01, which includes
peptides restricted by alleles in linkage with it; no deconvolution was done, so
the restricting allele is not identified (§20, D032).

**The predictor comparison cannot separate architecture from cohort-specific
training.** The CNN trained on 42 participants of this cohort — same laboratory,
same two instruments, same protocol, same negative construction over this
cohort's own expressed proteins — and MHCflurry never saw it. R10 bounds the
instrument part of that head start at 0.04–0.06 AP; the rest is unquantified.
The task itself is largely shared, not mismatched: MHCflurry's processing model
trains on observed-versus-unobserved discrimination at 1:1 with 65% same-protein
decoys, which is nearly the set-C construction. **An earlier draft of
`QC_G11.md` claimed a task mismatch and was wrong in this project's favour**;
the correction is recorded there. §18 shows the CNN adds information on this
cohort's task. It does not show the CNN is a better model of HLA presentation.

**Two predictors named in §18's own input list were never obtained.** NetMHCpan
4.1 sits behind a per-user academic licence form at the DTU host, which is not
scriptable and not mine to accept on the owner's behalf. MixMHCpred is
distributed through `raw.githubusercontent.com`, which this environment's proxy
refuses while allowing release assets. The comparison rests on one predictor
family, in two release lines.

### Limitations of the process

**The preregistration establishes integrity, not chronology.** The freeze record
proves the artifacts match it and fixes ordering within the repository. It does
**not** provide independent third-party evidence that it preceded seeing any
result, because it is created by the repository owner with the owner's clock
(D009).

**The model specification was frozen after the data was in hand.** §§11–13 were
fixed on 2026-10-06, after extraction and dataset construction, and were found
unfrozen only while the Methods section was being written. No model had been
fit and no performance figure existed, so no outcome could have influenced them
— but the length distribution was known, and it motivated the centre-padding
choice. That choice is defensible on its own terms and is declared in §12, but
it is not blind to the data and should not be described as though it were.

**Several design parameters were chosen by simulation under an assumed model.**
The per-participant cap, the interval calibration and the decision threshold all
rest on a binormal score model with an assumed between-participant variance that
cannot be measured until the model runs. The figures bound the design; they do
not describe it.

**Two preregistered reading rules were written so that their own designs could
not satisfy them, and one was narrowed after it failed.** D029 required a
symmetric confirmation from two groups that are not symmetric — carriers share
an allele, non-carriers share only its absence and span 41 alleles, a figure
printed in D029's own table. D031 then required a nominal-99% interval from a
6-unit arm, whose size D031 also printed. The second was narrowed by D032 and
the narrowing was **accepted by the project owner**, with the §20 wording fixed
in the same entry and the case against narrowing left in place unaltered. That
is the most reader-dependent step in this report: a criterion that bends after
it fails is not a criterion, and the only defences are that the failing
condition was unattainable by construction, that the narrowing was decided by
the owner rather than the author, and that the commit history carries the order.
**A reader who rejects those defences should treat §20 as unsupported and the
allele result as it stood before D032 — suggestive, not established.**

**One reported result was void and is kept in the repository.** D029's
allele-enriched stratum was defined as "observed in one arm's training pool and
absent from the other's", which guaranteed that one arm had memorised it: 97.93%
of its rows against 0.00%. Its +0.0660 was the largest number that run
produced. It is superseded by +0.0335 on rows neither arm saw, and D030 records
it rather than deleting it. It was the second instance of one failure mode — the
first `TEST_LEAKFREE` mask selected a subset with no negatives and returned a
perfect 1.0000 — and **both times the broken version produced the most
flattering number available.** The standing check D030 added exists because that
pattern is not a coincidence.

**One run previewed a preregistered result before the real run.** Validating the
multi-allele code required executing Part B end to end, which computed its
contrasts: the direction was visible at 2 epochs and one seed before the full
run started. Disclosed in D031. Nothing remained to choose — every parameter was
fixed and committed first — but a reader must take the commit order on trust.
The practice that avoids it is to validate plumbing on scrambled group labels.

**Estimates made during this work were checked against outcomes, and one was
badly wrong.** The eligible-peptide count was projected at 1.55M from five
participants and measured at 2,658,972 — an error of −41.8%, in the direction
that made the compute budget optimistic. The compute gate was consequently
breached twice. This is recorded because a projection never checked against its
outcome teaches nothing, and because it is the clearest available evidence about
how much weight the remaining simulation-based figures should carry.

## Conclusion

**The null is rejected. A small convolutional network distinguishes observed
HLA class-I peptides from unobserved peptides of the same source proteins, in
participants it never saw, at a mean per-participant average precision of
0.7551 — nominal-99% interval [0.7368, 0.7721] against a preregistered
threshold of 0.647.** The partition was read once, under a rule fixed before any
model existed.

Three preregistered checks then bounded what that number means, and the pattern
across them is the result worth carrying.

**It is not memorisation.** 15.99% of test positives appear verbatim in
training, and removing them leaves 0.7056 with a lower bound of 0.6926 — still
clearing the threshold. Leakage inflates the estimate by 0.0495 and does not
carry it.

**It is not the instrument.** Trained on one mass spectrometer and tested on the
other, performance does not collapse: 0.6959 and 0.7108, roughly 0.10 above each
pairing's own composition floor. A matched control puts the platform's cost at
**0.04–0.06 AP**, from four estimates across two designs with no interval
containing zero. The confound D005 accepted as irreducible is real, measured,
and smaller than the signal.

**Part of it is allele-specific, for one allele.** A model trained on carriers
of HLA-A\*02:01 ranks peptides exclusive to carriers above a model trained on
carriers of a different allele, by **0.048** average precision (nominal-99% CI
0.031–0.063) in **9 of 9** held-out participants, with memorisation, peptide
recurrence and training-set quality each measured at zero on the same units. The
direction reproduces across five alleles. It is not demonstrated for
HLA-C\*07:02, and the symmetric test cannot be replicated in this cohort.

**And it exceeds an off-the-shelf predictor on this task.** On rows neither
system has seen, the CNN leads MHCflurry by 0.134–0.138 average precision in all
ten held-out participants — a margin that survives the strictest subsetting and
is largest where contamination is smallest. It is not a verdict on
architectures: the CNN trained on this cohort's own instruments and negative
construction, and MHCflurry did not.

### What the design work established, independent of the result

A public submission was mapped to 52 participants with complete provenance and
no unresolved joins; 2,658,972 unique peptides were extracted with every
container verified against its publisher checksum; and the dataset, split,
endpoint and decision rule were fixed in advance with checksums.

**Three measurements constrain what any result on this dataset can mean, and all
three were unknown when the experiment was proposed.** Performance must be read
against a composition-only floor of **0.597**, not chance. Participant-disjoint
splitting delivers **15.99%** sequence leakage. And the acquisition instrument is
separable from the peptide sequences alone at AUROC **0.645** against **0.515**
for a control.

**That last one stands independent of this experiment entirely.** Any analysis of
this dataset holding out participants — the standard design — inherits the same
confound, measured or not. It belongs to the dataset, not to this study.

**A fourth measurement arrived from outside.** An independently trained
predictor ranks 11.78% of this study's negatives as strong presenters. The
negative class is contaminated at roughly one in nine, which depresses every
figure above, the endpoint included.

### What changed most

**The hypothesis.** As proposed, §25 asked whether the network beats chance — a
test simulation showed it passing at AUROC 0.60 with certainty, so it could not
have failed. It was rewritten to ask whether the network beats a measured floor
by a specified margin, on an interval calibrated to its actual coverage, at a
threshold chosen for power. **The question became capable of coming out the
other way, and then it came out this way.** That ordering is the only reason the
answer is worth having.

### What this still cannot claim

Not that the 0.158 lift is presentation biology: the confounds both platforms
and both allele groups *share* — source-protein abundance, detectability bias,
the negative construction itself — are untouched by every analysis here. Not
that the restricting allele is identified, since no deconvolution was done. Not
anything beyond one submission, one laboratory, one disease, one tissue, with no
external replication anywhere in the design. And not §20 at all, for a reader
who declines the criterion narrowing that D032 records and the Limitations
section flags as this report's most reader-dependent step.

**External replication remains the largest gap, and it is the same gap the
design work identified before the model ran.** A second dataset with a different
instrument distribution would do more than any analytic refinement here: it
would break the platform confound that no split over these participants can
touch, and it is the only route to the symmetric allele test this cohort cannot
supply.

## References

According to PubMed, one reference has been retrieved and verified:

| Reference | Identifiers | Role |
|---|---|---|
| O'Donnell TJ, Rubinsteyn A, Laserson U. *MHCflurry 2.0: Improved Pan-Allele Prediction of MHC Class I-Presented Peptides by Incorporating Antigen Processing.* Cell Syst. 2020;11(1):42–48.e7 | [DOI 10.1016/j.cels.2020.06.010](https://doi.org/10.1016/j.cels.2020.06.010) · PMID 32711842 | §18 comparison predictor (S6) |

Retrieved via PubMed and used to correct `QC_G11.md` §4: the paper states the
processing model is trained to discriminate observed mass-spec ligands from
unobserved peptides, which withdrew a task-mismatch caveat this report had been
making in its own favour. An earlier provenance record in
`data/raw/S6/provenance.jsonl` carries this citation **without the `.e7` page
extension**, because it was written from memory before being checked; the row
above is the verified form.

Still not retrieved:

| Reference | Status |
|---|---|
| PXD024871 submission description / dataset publication (S7) | **not retrieved.** The submission's own files are retrieved (S1–S3, S5); the accompanying publication is not, and is not asserted from memory |
| Allele nomenclature specification | **not retrieved.** Required for M4 validation; allele strings are used as the SDRF reports them, normalized but not validated against the specification |
| NetMHCpan 4.1, MixMHCpred publications | **not retrieved**, because neither predictor was obtained |

No other citation appears anywhere in this report. Where a factual claim about
the wider literature would have been needed, it was either verified as above or
left out.

## Tables and Figures

### Design, written before any model ran

| ID | Title | Source | Generated by |
|---|---|---|---|
| T1 | Design resolution grid, 91 rows | `results/power/power_grid.csv` | `power_analysis.py` (run-001) |
| T2 | Run parameters and reconstruction note | `results/power/power_params.json` | `power_analysis.py` (run-001) |
| T3 | Measured throughput and derived grid cost | `results/compute/benchmark.json` | `benchmark_compute.py` (run-002) |
| T4 | Per-unit cap precision curve | `results/power/subsample_curve.json` | `subsample_curve.py` |
| T5 | Interval coverage and power at the adopted rule | `results/power/decision_rule.json` | `calibrate_decision_rule.py` |
| T6 | Negative-set composition diagnostic, sets A/B/C | `results/qc/negative_diagnostic.json` | `negative_diagnostic.py` |
| T7 | Leakage audit over 2,000 random splits | `results/qc/leakage_audit.json` | `leakage_audit.py` |
| T8 | Peptide-universe statistics | `results/qc/union_stats.json` | `union_analysis.py` |

### Results

| ID | Title | Source | Generated by |
|---|---|---|---|
| T9 | Selection grid, 16 configurations × 5 folds | `results/model/cv_results.json` | `train_cnn.py --mode cv` |
| T10 | Final fit, 25 models | `results/model/final.json` | `train_cnn.py --mode final` |
| T11 | **Primary endpoint**, per-unit and pooled | `results/model/endpoint.json` | `train_cnn.py --mode test` |
| T12 | Endpoint decomposed by peptide length | `results/model/endpoint_by_length.json` | `endpoint_by_length.py` |
| T13 | Cross-platform transfer, 4 arms + 4 contrasts | `results/model/transfer.json` | `train_cnn.py --mode transfer` |
| T14 | Transfer post-hoc: CNN vs composition penalty | `results/model/transfer_posthoc.json` | inline, recorded in QC_G12 |
| T15 | Dominant-allele-held-out, 3 arms | `results/model/allele.json` | `train_cnn.py --mode allele` |
| T16 | The same, corrected for memorisation | `results/model/allele_leakfree.json` | `allele_leakfree.py` |
| T17 | Neutral training-set-quality estimate | `results/model/allele_neutral.json` | inline, recorded in QC_G12 |
| T18 | Multi-allele test, 5 alleles + the symmetric pair | `results/model/multi_allele.json` | `multi_allele.py` |
| T19 | Multi-allele difference-of-differences | `results/model/multi_allele_dod.json` | inline, recorded in QC_G12 |
| T20 | Predictor contamination, both release lines | `results/qc/predictor_contamination.json` | `predictor_contamination.py` |
| T21 | **§18 comparison**, 3 row sets × 3 systems | `results/predictors/comparison_with_predictors.csv` | `compare_predictors.py` |
| T22 | Negative-class contamination, measured externally | `results/qc/predictor_task_mismatch.json` | inline, corrected 2026-10-07 |

### Figures

| ID | Title | Source | Generated by |
|---|---|---|---|
| F1–F6 | Methodology flowcharts: pipeline, mapping dataflow, status resolution, gate handling, decision order, scope constraint | `FLOWCHART.md` | Hand-authored; Mermaid grammar validated |

**No figure is plotted from project data.** Every quantitative result in this
report is a table, and each one names the artifact and the script that produced
it. That is a presentational gap, not a missing analysis: the numbers are in
`results/` with their provenance, and a reader who wants a plot has the inputs.

### QC gate records

`results/qc/` carries `QC_G1`–`QC_G6`, `QC_G3_pilot`, `QC_G4_prep`, `QC_G5`,
`QC_G7_cv`, `QC_G10_endpoint`, `QC_G11`, `QC_G12_transfer`, `QC_G12_allele` and
`QC_G12_multi_allele`. Each states what passed, what was reduced or deferred and
why, and the gate schedule in `SECTIONS.md` forbids silent reduction.
