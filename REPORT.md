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

**A design and preregistration report.** It documents the retrieval and
provenance mapping of the source submission, the construction and freezing of an
analysis dataset and an evaluation split, the diagnostics that selected the
negative controls and calibrated the statistical procedure, and the decision rule
fixed in advance for the primary hypothesis.

**No model has been fit.** There is no result here about the hypothesis. The
measurements reported are properties of the dataset and the design, and the
Discussion is explicit that it discusses the design rather than the question.

This ordering is the point. Each of the hazards above was quantified before the
corresponding design choice was made: the negative construction was selected on a
composition diagnostic, the per-participant sample size on a precision curve, the
reporting interval on measured coverage, and the decision threshold on measured
power. Where a quantity could not be measured in advance, the handling was fixed
as a protocol so it could not be chosen once the answer was known.

The result of that ordering is a narrower question than the one originally posed,
with the narrowing documented rather than discovered later. The Discussion sets
out how much narrower, and the Limitations section states what the study will
not be able to claim regardless of what the model does.

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
`f7550f54`, with artifact checksums recorded in `PREREGISTRATION.md`. That
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

### Software and environment

Phase A and dataset construction use only the Python standard library. The
design analyses use numpy 2.4.6 and scipy 1.17.1. Environments are recorded in
`ENVIRONMENT.md`: `env-001` (4-core cloud container, no GPU) for analysis,
`env-002` (Colab, 2 cores) for extraction. Measured training throughput for the
benchmarked configuration is 122,648 peptides/second on `env-001`, from which
the compute budget derives and to which it does not port.

## Results

All results to date concern the dataset and the design. **No model has been fit**,
so none bears on the primary hypothesis. Interpretation is deferred to the
Discussion; this section reports measurements.

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

No model has been fit. There is therefore no value for the primary endpoint, no
held-out performance, no per-participant distribution, no predictor comparison,
and no result bearing on the primary or secondary hypotheses. Training requires
hardware beyond the environment used for this work.

## Discussion

**This discusses the design, not the hypothesis.** No model has been fit, so
nothing here is a finding about whether a convolutional network can distinguish
these peptides. What the work to date establishes is narrower and worth stating
plainly: what question this dataset can actually answer, and how much narrower
that is than the question asked.

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

### Interpretation is pre-committed, before any result exists

Mapping the proposal's §21 outcomes onto the measured design, so that the
reading of each is fixed now rather than negotiated afterwards:

| Result | Reading |
|---|---|
| Rejects the null, holds within platform **and** across platform | The strongest reading available: sequence carries signal that survives both unseen participants and unseen instrument conditions. Still bounded to one disease, one tissue, one laboratory |
| Rejects, but collapses in cross-platform transfer | The signal is substantially instrument, not presentation. §25 would not be supportable as stated |
| Rejects on the full test partition but not on the leakage-free subset | Memorisation of the 15.99% overlap, not generalization |
| Fails to reject | **Not** evidence of absent signal. Power is 0.42 at AUROC 0.70, so a real effect below a lift of ~0.14 is more likely to be missed than found |
| Very high performance with any leakage or control check failing | Not interpretable biologically until resolved, per proposal §21 Outcome E |

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

**Nominal intervals under-cover — measured.** Nominal 95% cluster-bootstrap
intervals achieve 0.884–0.890 actual coverage at this participant count.
Reporting is at nominal 99% to deliver approximately 95%; any figure quoted at
nominal 95% elsewhere would overstate precision by that margin.

### Limitations of the data itself

**Negative labels are not evidence of non-presentation.** Negatives are peptides
not observed, and non-observation conflates genuine absence with detection
limits. The repertoires are deeply undersampled — redundancy across participants
is 1.45× and the 52nd participant added was still 55% novel — so the negative
class is contaminated at an unknown rate. This biases measured performance
**downward** and is inherent to any construction built on absence.

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

**Fourteen of 52 participants are incompletely typed** and are excluded from
analyses keyed on the full allele complement. The allele-disjoint secondary
split is also costly: holding out the 29 carriers of the most common allele
leaves 23 for training.

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

**Estimates made during this work were checked against outcomes, and one was
badly wrong.** The eligible-peptide count was projected at 1.55M from five
participants and measured at 2,658,972 — an error of −41.8%, in the direction
that made the compute budget optimistic. The compute gate was consequently
breached twice. This is recorded because a projection never checked against its
outcome teaches nothing, and because it is the clearest available evidence about
how much weight the remaining simulation-based figures should carry.

## Conclusion

No conclusion about PXD024871 is available, and none should be inferred from
this document. The statistical design has been bounded and found viable for a
coarse claim, conditional on raising the hypothesis threshold (D008) and
restating the sample-size gate in participants rather than peptides (D007).
Whether sufficient eligible data exist is unknown and blocked on retrieval.

## References

| ID | Reference | Status |
|---|---|---|
| — | PXD024871 submission, PRIDE Archive | Not retrieved (S1–S4) |
| — | Dataset publication | Not retrieved (S7) |
| — | Allele nomenclature specification | Required for M4 validation; not retrieved |
| — | Comparison predictor publications | Required for §18; not retrieved (S6) |

No reference has been retrieved or verified. Citations will be added as sources
are acquired; none is asserted from memory.

## Tables and Figures

| ID | Title | Source | Generated by |
|---|---|---|---|
| T1 | Design resolution grid, 91 rows | `results/power/power_grid.csv` | `scripts/power_analysis.py` (run-001) |
| T2 | Run parameters and reconstruction note | `results/power/power_params.json` | `scripts/power_analysis.py` (run-001) |
| T3 | Measured throughput and derived grid cost | `results/compute/benchmark.json` | `scripts/benchmark_compute.py` (run-002) |
| F1–F6 | Methodology flowcharts: pipeline, mapping dataflow, status resolution, gate handling, decision order, scope constraint | `FLOWCHART.md` | Hand-authored; Mermaid grammar validated |

No figure has been generated from project data, because no project data exists.
