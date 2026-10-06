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

| Component | Specification | Status |
|---|---|---|
| Mapping chain | Seven joins M1–M7, each under the prompt's eleven fields | Specified, not executed |
| Source provenance | Seven sources S1–S7, twelve fields each, `DATA_SOURCES.md` | Schema only; nothing retrieved |
| Status categories | Per mapping, *Confidence/status categories*; weakest-link composition in M6 | Specified |
| Normalization | `METHODOLOGY.md`, *Shared normalization conventions* | Specified |
| Approximate matching | Prohibited on all identifier joins, argued in M1 | Specified; departure from `PROJECT_PROMPT.md`, logged as D016 |
| QC gates | G1–G13, `METHODOLOGY.md`, *QC gates*, and `SECTIONS.md` | Specified; none attempted |
| Design analysis | Binormal simulation, `scripts/power_analysis.py` | **Complete** (run-001) |

Two rules are stated as prohibitions rather than preferences, because both
would manufacture assertions the sources do not make: class is never inferred
from filenames (M3), and incomplete genotypes are never imputed to
completeness (M4).

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
| F1–F6 | Methodology flowcharts: pipeline, mapping dataflow, status resolution, gate handling, decision order, scope constraint | `FLOWCHART.md` | Hand-authored; Mermaid grammar validated |

No figure has been generated from project data, because no project data exists.
