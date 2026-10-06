# REPORT

Continuously updated report required by `PROJECT_PROMPT.md` §7. Every claim
below links to the analysis, artifact, or decision that supports it.

**State as of 2026-10-06:** no dataset has been retrieved. The only completed
analysis is a design-resolution study (run-001). Nothing here is an empirical
finding about PXD024871.

---

## Introduction

The project asks whether a sequence-based 1D CNN can distinguish experimentally
observed HLA class-I-associated peptides from constructed negative controls,
and whether any learned signal generalizes to biological units absent from
training. The experiment is specified in
`PXD024871_CNN_Experiment_Proposal.md` (committed unmodified).

The CNN is downstream of provenance mapping and is never an input to it: no
model output may assign a file to a class, a run to a unit, or a peptide to a
participant (`METHODOLOGY.md`, *Scope constraint*; proposal §1, §28).

Before the experiment can run, the deposited submission must be resolved into
an analysis-ready peptide table whose every row traces to a deposited file.
That mapping is the current work.

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

### R1 — Design resolution (run-001)

The only result to date. Full write-up in `POWER_ANALYSIS.md`; record in
`RUN_LOG.md` run-001; data in `results/power/power_grid.csv` (91 rows).

| Finding | Evidence | Consequence |
|---|---|---|
| The proposal's primary hypothesis is near-unfalsifiable — power 1.00 in all 54 cells, and at a mean AUROC of 0.60 | `POWER_ANALYSIS.md` F1 | D008 must specify a lift, not a direction |
| Resolution is set by held-out participant count, not bootstrap replicates: B from 200→50,000 moves the half-width <0.002; K 10→26 cuts it 35% | F2 | Proposal §16's B=10,000 is not a precision lever |
| Nominal 95% intervals achieve 0.66–0.95 actual coverage; ~0.80 at K=5 | F3 | Intervals must be reported as approximate |
| At a 1:100 class ratio the AP estimator is biased upward by ~10% of the lift, and that bias exceeds interval width as a source of miscoverage | F4 | Statistical argument against extreme ratios, independent of composition (D002) |
| Between-participant variance is the dominant unknown; half-width swings 5× across its plausible range | F5 | Achievable precision is bounded, not yet knowable |
| Paired predictor comparison is better powered at every K; MDE ≈ 0.05 AP at K=10 | F7 | D014 (ratified): §18 preregistered as secondary, not promoted — its weakness is an unverifiable dependency |

Estimators were cross-validated before use: analytic average precision returns
prevalence exactly at zero discrimination, agrees with the empirical estimator
to three decimals, and is insensitive to integration grid resolution
(`RUN_LOG.md` run-001, Validation performed).

### R2 — Retrieval

Attempted and blocked. The execution environment's network policy denies the
distribution host; the failed attempt is retained at
`data/raw/S1/provenance.jsonl` with `outcome: FAILED`
(`DATA_SOURCES.md`, Blocked retrievals).

No count describing PXD024871 anywhere in this repository has been verified.
All such figures are marked `[provisional]` and originate from a description
supplied in conversation, not from a retrieved file.

### R3 — Compute budget (run-002)

Measured throughput on the target machine: ~123,000 peptides/sec training on
four cores with no GPU. Worst-case grid — 100,000 positives at 1:10, 20
configurations across 5 folds plus a 5-seed final fit — comes to about 31 hours
against a 48-hour cap. Limits and the preregistered reduction ladder are in
`SECTIONS.md` §14; basis in `DECISION_LOG.md` D020.

Two incidental findings. **No GPU is required** — the architecture is small
enough that CPU suffices, removing a dependency the proposal left implicit.
**Streaming the identification containers is forced rather than chosen** — 30 GB
of writable disk against a set now verified at 107.53 GiB, so the
stream-and-delete strategy in `DATA_SOURCES.md` is the only feasible route, and
its reproducibility cost is a constraint rather than a trade. Peak working space
is ~12 GiB, the largest single container being 9.25 GiB — corrected upward from
a ~2 GB figure that predated any measurement.

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
