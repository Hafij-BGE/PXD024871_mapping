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

**The preregistration is incomplete in one respect, stated here rather than
discovered later.** Sections 11, 12 and 13 of the experiment specification — the
network architecture, the input representation, and the training protocol —
remain unlocked. The configuration used for throughput benchmarking (length-12
input, 32-dimensional embedding, two 64-filter convolutions with kernel width 3,
64-unit dense layer) was chosen to size the compute budget, not as a
preregistered architecture. Until those sections are frozen there is latitude in
exactly the component whose behaviour the experiment measures, and any
confirmatory claim must either follow their freezing or be reported as
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

The design analysis changes the experiment's framing more than its feasibility.
The proposal is not underpowered; it is mis-specified at two points. Its
primary hypothesis would pass for a classifier of negligible practical value
(R1/F1), and its stated precision mechanism — bootstrap replicates — does not
control precision (R1/F2). Both are correctable by specification rather than by
collecting more data.

The more useful finding is R1/F7: pairing removes the between-participant
variance that bounds the absolute claim, so the comparison against existing
predictors is the better-powered question at this sample size. That suggests
the confirmatory endpoint may be in the wrong place. D014 weighed that against
M7 and was ratified the other way: §25 stays primary because its flaw is a
missing threshold, which can be written, whereas §18's flaw is an unverifiable
dependency on the comparison predictors' training data, which cannot be
resolved from inside this project. §18 is preregistered as secondary and
reported regardless. A well-specified weaker claim was preferred to a
better-powered one resting on an unchecked premise.

R1/F4 is a caution about the primary metric itself. AUPRC is not merely
imprecise at extreme class imbalance; it is biased in the flattering direction,
and no amount of resampling corrects it.

## Limitations

Methodological limitations of the approach are enumerated at
`METHODOLOGY.md`, *Known methodological limitations* (ten items, including
participant-bounded resolution,
platform confounding, and that absence of observation is not negative
evidence). Limitations of run-001 specifically are at `POWER_ANALYSIS.md`,
Limitations (seven items).

The limitation governing everything else: **Phase A asserts only what the
deposited annotation asserts.** An error in the source metadata propagates
through every mapping and is undetectable from inside this pipeline, except
where independent verification (`METHODOLOGY.md`, *Independent verification*)
happens to cover it.

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
