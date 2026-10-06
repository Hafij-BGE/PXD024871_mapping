# METHODOLOGY

Mapping methodology for PXD024871. Written before execution; this document is
the specification, not a report of what happened.

**Governed by `PROJECT_PROMPT.md`.** This file supplies the dataset-specific
content its *Mapping Methodology* section requires. Every mapping below is
documented under that section's eleven fields, in its order, verbatim as
headings.

**Restructured 2026-10-06** from an earlier organisation of my own (numbered
join, normalization and status schemes). Two things were kept and should be
seen for what they are:

- **The `M1`–`M7` tags are labels, not a framework.** They exist only so
  `FLOWCHART.md`, `REPORT.md` and `DATA_SOURCES.md` can cross-reference a
  specific mapping. They carry no meaning beyond naming.
- **Shared normalization conventions are stated once below** rather than
  repeated under all seven *normalization rules* fields, which would duplicate
  the same eight lines seven times. Each mapping names which apply plus
  anything specific to it. This is a compression of the prompt's structure, not
  a departure from it, and it is flagged here rather than done quietly.

The experiment served is `PXD024871_CNN_Experiment_Proposal.md`, committed
unmodified. Figures are **verified from the retrieved sources** as of 2026-10-06 (S1 and
S2; see `results/qc/QC_G1.md` to `QC_G3.md`). Anything still unverified is
marked **[provisional]** and now concerns only the identification containers,
which are not yet retrieved.

**Two rules from the prompt govern everything below.** Never silently force an
ambiguous match. Every mapping decision must be traceable to its evidence.

---

## Shared normalization conventions

Applied wherever a key is compared. Normalization is for comparison only; the
original value is retained verbatim in a `*_raw` column beside every key.

Unicode normalized to NFC. Leading and trailing whitespace stripped, internal
runs collapsed to one space. Case folded for comparison, never in storage.
Directory components stripped; basenames compared. File extensions retained as
part of identity. Multi-value fields split on the delimiter observed in the
file and recorded per field, never on a guessed delimiter. Absent, empty-string
and sentinel values distinguished from each other, all three treated as
unmatched, with the distinction recorded. Numeric identifiers compared as
strings — leading zeros are significant and never stripped, because identifiers
differing only by leading zeros or a single digit are distinct entities and
numeric coercion silently merges them.

## Scope constraint

The CNN is downstream of every mapping here and is never an input to one. No
model output may assign a file to a class, a run to a unit, or a peptide to a
participant. Restates proposal §1 and §28 as an operational constraint: any
code path from a model artifact back into a mapping table is a defect.

---

# M1 — Deposited file to metadata row

**What is being mapped.** The deposited file inventory onto the sample-metadata
rows that describe each acquisition, establishing which deposited files the
metadata actually accounts for.

**Source entity.** Deposited filename, as published in the repository file
manifest.

**Target entity.** Sample-metadata row, keyed on its data-file reference column.

**Matching criteria.** Equality of normalized basename.

**Normalization rules.** Shared conventions: NFC, whitespace, case folding,
path stripping, extension retention, string comparison of identifiers.

**Exact-match rules.** One manifest filename to exactly one metadata row.
Expected cardinality 1:1 across the acquisition files. **Verified:** 402
acquisitions against 402 metadata rows, 402 matched, zero unmatched in either
direction, zero rejects (`QC_G1.md`).

**Approximate/fuzzy matching rules.** **Prohibited.** Run filenames in this
submission differ by one character between genuinely different acquisitions,
so any edit-distance threshold loose enough to repair a typo is also loose
enough to merge two distinct acquisitions, silently and unrecoverably. A
near-miss is recorded as a candidate for human adjudication, with both
normalized keys and the edit distance, and stays unmatched until adjudicated by
a logged decision — never by the matcher.

**Ambiguity handling.** One row referencing two or more manifest files, or one
file matched by two or more rows, is ambiguous. Both are written to the rejects
file with the full candidate set and excluded from the eligible set. No
candidate is selected.

**Unmatched records.** Reported in both directions separately: acquisitions
with no row, and rows referencing files absent from the manifest. A left-only
count is not evidence of completeness. Identification containers and the
metadata file itself appear in the manifest with no row of their own; these are
classified out-of-scope rather than unmatched, and the out-of-scope set is
enumerated explicitly so the category cannot absorb a genuine failure.

**Duplicate handling.** Manifest basenames must be unique after normalization.
A collision means two deposited files normalize to one key; it is a conflict,
blocks the gate, and is not resolved by picking either.

**Confidence/status categories.** `EXACT` (deterministic single match),
`AMBIGUOUS`, `UNMATCHED`, `OUT_OF_SCOPE`, `CONFLICT`. Only `EXACT` is eligible.

**Outputs and gate.** `FILE_MAP.csv`, `FILE_MAP_REJECTS.csv`; gate G1.

---

# M2 — Metadata row to biological unit

**What is being mapped.** Acquisitions onto the independent biological units
used for splitting and resampling.

**Source entity.** Metadata row attributes: participant identifier, biological
replicate, technical replicate, fraction identifier.

**Target entity.** `unit_id`.

**Matching criteria.** `unit_id` derived from the participant identifier alone.
Replicates and fractions are attributes *within* a unit, not units. Several
rows mapping to one `unit_id` is the expected case, not an error.

**Normalization rules.** Shared conventions, with particular weight on string
comparison of identifiers: participant identifiers differing by one digit are
different individuals.

**Exact-match rules.** A row maps to the unit named by its participant
identifier. No unit is created, merged or inferred beyond what the identifier
states.

**Approximate/fuzzy matching rules.** Prohibited, for the reason given under
M1. Participant identifiers are the densest near-neighbour space in the
submission.

**Ambiguity handling.** Rows sharing a participant identifier but carrying
contradictory unit-level attributes are a conflict: recorded, excluded, not
reconciled by preference.

**Unmatched records.** A row with an absent participant identifier is
unmatched. The unit is **not** inferred from filename, acquisition order, or
position in the file.

**Duplicate handling.** Expected and retained. Runs, replicates and fractions
are counted per unit and reported; none is collapsed.

**Confidence/status categories.** `EVIDENCED` (identifier present),
`CONFLICT`, `UNMATCHED`. Status composes downstream: a peptide's status is the
weakest in its chain, and no later step may upgrade it.

**A forced choice, not a fact.** Treating the participant as the unit asserts
that replicates and fractions are not independent observations. That is the
defensible reading and the conservative one — it yields the smallest unit count
and therefore the widest uncertainty intervals. Treating replicates as units
would inflate apparent sample size and narrow intervals around a statistic
whose real resolution is set by participant count. Logged as D011 so the choice
is on the record rather than embedded in code. Consequence: the resampling unit
in proposal §16 is `unit_id`, and run-001 confirmed the bootstrap's resolution
is bounded by unit count, not by B.

**Outputs and gate.** `UNITS.csv` with per-unit run, replicate and fraction
counts; gate G3.

---

# M3 — Metadata row to enrichment class

**What is being mapped.** Acquisitions onto the class of material enriched,
determining which acquisitions are eligible for the experiment at all.

**Source entity.** The row's enrichment-reagent annotation.

**Target entity.** `hla_class` in {`I`, `II`, `UNKNOWN`}.

**Matching criteria.** Lookup against an explicit, version-controlled
controlled-vocabulary term table.

**Normalization rules.** Shared conventions, plus multi-value splitting on the
delimiter observed in the annotation field.

**Exact-match rules.** Enumerate the distinct reagent strings present in the
file **first**; map each one deliberately in `vocab/enrichment_class.tsv`. A
string absent from the table raises an error and halts the stage rather than
defaulting.

**Approximate/fuzzy matching rules.** **Prohibited, including substring and
keyword matching on reagent names.** A term table is small and auditable;
substring matching on reagent names is neither, and can silently misclassify a
whole acquisition group.

**Ambiguity handling.** A row annotating reagents that map to more than one
class is ambiguous: `UNKNOWN`, excluded, recorded with its candidate classes.

**Unmatched records.** Annotation absent or unmappable gives `UNKNOWN` and
exclusion from the eligible set. **Class is never inferred from filenames**
(proposal §5 A2) — this is stated as a prohibition because it is the tempting
shortcut and it would manufacture an assertion the metadata does not make.

**Duplicate handling.** Many rows share a reagent annotation; this is expected.
Row counts per distinct annotation are reported at the gate.

**Confidence/status categories.** `EVIDENCED` (depositor annotation),
`AMBIGUOUS`, `UNKNOWN`. There is no inferred category, by design.

**Traceability.** `source_evidence` records the literal annotation string that
produced each assignment, so every class label is auditable to its source cell
without re-reading the metadata file.

**Outputs and gate.** `hla_class` and `source_evidence` in `FILE_MAP.csv`;
`ELIGIBILITY.csv`; gate G2. **Verified:** exactly two distinct annotations,
partitioning cleanly into 222 class-I and 180 class-II runs. The independent
check held — `characteristics[mhc protein complex]` agrees on 402/402 rows with
zero conflicts (`QC_G2.md`).

---

# M4 — Biological unit to genotype

**What is being mapped.** Participants onto their recorded allele sets — the
evidence base for whether the proposal's §25 generalization claim can be
distinguished from a claim about participant-level batch independence.

**Source entity.** Per-participant typing annotation, free text.

**Target entity.** Normalized allele set per `unit_id`.

**Matching criteria.** Parse, validate against nomenclature, canonicalize to
two-field resolution.

**Normalization rules.** Shared conventions, then nomenclature
canonicalization. Validation is against the published nomenclature
specification, not against our own pattern.

**Exact-match rules.** Each token must match the standard two-field allele
designation pattern. Tokens failing validation are retained verbatim and
flagged — never discarded, never repaired.

**Approximate/fuzzy matching rules.** Prohibited. Allele designations differing
by one field are different alleles.

**Ambiguity handling.** Tokens below two-field resolution, or carrying an
ambiguity code, are retained, flagged, and excluded from allele-stratified
analyses.

**Unmatched records.** Participants with no typing annotation are recorded as
absent and excluded from allele-stratified analyses only — they remain eligible
for participant-level analysis.

**Duplicate handling.** A repeated allele within a participant may be genuine
homozygosity or a duplicated entry; both are recorded as observed, neither is
collapsed.

**Confidence/status categories.** `COMPLETE` (full complement at two-field),
`PARTIAL` (fewer loci resolved than expected), `LOW_RESOLUTION`, `ABSENT`.

**Imputation is prohibited.** A participant with fewer recorded alleles than
loci is indistinguishable, from this metadata alone, between genuine
single-allele loci and incomplete reporting. Both are real and the metadata
does not separate them. Filling the gap by duplicating an observed allele would
manufacture an assertion the source does not make. Such participants are
`PARTIAL`: usable for participant-level analysis, excluded from any analysis
keyed on the complete complement. Logged as D012.

**Why this mapping exists.** The allele-frequency table it produces determines
whether an allele-disjoint split is constructible at all. If common alleles are
shared across most participants, it is not, and the §25 claim must be reworded
rather than tested. That is the cheapest point in the project at which the
headline claim can change.

**Outputs and gate.** `UNIT_GENOTYPE.csv`, allele-frequency table; gate G2.

---

# M5 — Identification container to acquisition run

**What is being mapped.** Identification containers onto the acquisitions whose
spectra they searched.

**Source entity.** Identification container file.

**Target entity.** One or more acquisition runs in `FILE_MAP.csv`.

**Matching criteria.** Read the container's own internal record of its input
spectrum files; join those on normalized basename.

**Normalization rules.** Shared conventions, path stripping and extension
retention in particular.

**Exact-match rules.** Resolution comes from the container's internal table.
Filename-pattern inference is a flagged fallback, not the primary path, and
carries reduced status for every peptide downstream.

**Approximate/fuzzy matching rules.** Prohibited.

**Ambiguity handling.** An internal reference resolving to two or more manifest
files is ambiguous; recorded, and its peptides are not assigned a unit.

**Unmatched records.** An internal reference to a file absent from the manifest
is recorded; peptides from that reference get no unit assignment and are
excluded rather than attributed to a guess.

**Duplicate handling.** Expected fan-out: 101 containers against 402
acquisitions (verified from the manifest), implying aggregation. The true
fan-out is read from the containers' internal records, not inferred from that
ratio, and **[provisional]** remains until they are retrieved. Several containers referencing one
acquisition is also possible and is reported.

**Confidence/status categories.** `EXACT` (internal record), `PARTIAL`
(filename fallback), `AMBIGUOUS`, `UNMATCHED`.

**Outputs and gate.** `CONTAINER_RUN_MAP.csv`; gate G3.

---

# M6 — Peptide identification to biological unit

**What is being mapped.** Peptide identifications onto participants, producing
the analysis table. Introduces no new join — composition and filtering only.

**Source entity.** Peptide identification row within a container.

**Target entity.** `unit_id`, with class and genotype attached.

**Matching criteria.** Composition along the chain: peptide to container (M5),
container to acquisition, acquisition to metadata row (M1), row to unit (M2),
with class (M3) and genotype (M4) joined on.

**Normalization rules.** Sequence normalization only: case, whitespace, and an
explicit recorded rule for any non-standard residue representation.

**Exact-match rules.** Each link is the exact join already specified; no link is
re-derived here.

**Approximate/fuzzy matching rules.** Prohibited.

**Ambiguity handling.** A peptide whose chain contains an ambiguous link is
excluded, carrying the reason from the link that failed.

**Unmatched records.** Peptides from unresolvable containers or acquisitions
are retained in the observation table with a null unit and an explicit reason,
not dropped.

**Duplicate handling.** **A sequence observed in several acquisitions or
participants is not deduplicated here.** One row per observation is retained.
Unique-sequence collapse happens later and separately, because the collapse
rule depends on D003 — and the cross-participant sharing structure that D003
must decide on is only visible before collapse.

**Confidence/status categories.** The weakest status along the chain. A peptide
joined through an `EXACT` file match, an `EVIDENCED` class and a `PARTIAL`
genotype is `PARTIAL`. Weakening is monotonic.

**Filtering.** Eligibility and quality thresholds are frozen before any model
evaluation (proposal §6). Threshold selection is D004. Every row carries
container, acquisition, metadata row, unit, class, genotype, and the status of
each link.

**Outputs and gate.** `PEPTIDE_OBSERVATIONS.parquet`, then `POSITIVES.csv`;
gate G4.

---

# M7 — Peptide to external predictor training sets

**What is being mapped.** Analysis-table sequences onto the training data of
the comparison predictors, to detect contamination that would otherwise make
the proposal §18 comparison unfair in an unknown direction.

**Source entity.** Analysis-table sequence.

**Target entity.** Membership in each comparison predictor's training set.

**Matching criteria.** Exact normalized sequence equality.

**Normalization rules.** Sequence normalization as in M6, applied identically
to both sides.

**Exact-match rules.** Exact sequence identity only.

**Approximate/fuzzy matching rules.** Prohibited. A near-identical sequence is
a different peptide.

**Ambiguity handling.** None arises: membership is a set test.

**Unmatched records.** A sequence absent from an inspectable training set is
genuinely uncontaminated with respect to that predictor, and recorded as such.

**Duplicate handling.** Overlap counts are reported per predictor, and the
overlapping sequence list retained.

**Confidence/status categories.** `CLEAN`, `OVERLAPPING`, and
**`UNVERIFIABLE`** where a predictor's training set cannot be obtained.
`UNVERIFIABLE` is the point of this mapping: a comparison against a predictor
whose training data cannot be inspected is reportable only with that caveat
attached. Treating it as clean would misstate the CNN's position without
knowing in which direction.

**Bearing on D014, now decided.** Because §18's weakness is an `UNVERIFIABLE`
this pipeline cannot resolve, making it the confirmatory endpoint would rest the
headline claim on an uncheckable assumption. D014 is ratified on that basis:
§25 stays primary with a raised threshold, §18 is preregistered as secondary.
**This mapping is the gate on revisiting that.** If M7 returns `CLEAN` or a
quantified `OVERLAPPING` for every comparison predictor, the objection
disappears and §18 may be promoted — by a new decision entry, before results
are seen. If any predictor returns `UNVERIFIABLE`, it may not.

**Outputs and gate.** Per-predictor overlap counts and sequence lists; gate G11.

---

## Traceability record

Per `PROJECT_PROMPT.md` §8, every executed stage records: what was done, why,
method, code, environment, input, parameters, output, QC, interpretation.
Satisfied by one entry per stage in `RUN_LOG.md` plus the referenced artifacts.
A stage whose inputs, code and parameters are all recorded with checksums is
re-runnable from that record alone — which is the reproducibility criterion:
not that the stage ran, but that it can be re-run from the documentation
without consulting whoever ran it.

## QC gates

Each gate is a named set of checks with pass/fail recorded per check. A FAIL
blocks progression until corrected, or until formally accepted as a limitation
by a logged decision. A gate is never partially passed.

| Gate | Stage | Checks |
|---|---|---|
| G1 | Retrieval & inventory | Checksum recorded for every retrieved file; published checksums verified where available; manifest count matches retrieval count; M1 reported in both directions; out-of-scope set enumerated |
| G2 | Class & genotype | Reagent vocabulary complete, no unmapped term; class counts per distinct term; genotype parse rate and failure list; allele frequency across units; typing completeness per unit |
| G3 | Units & containers | Every eligible row assigned a unit; unit count and per-unit run counts; container fan-out read from internal records; unassignable peptide sources listed |
| G4 | Peptide table frozen | Length distribution within declared range; threshold applied as preregistered; cross-unit sharing quantified; positive/negative overlap empty; class ratio fixed; minimum-N gate evaluated |
| G5 | Leakage & confounds | No sequence crosses splits except as D003 permits; no unit crosses splits; acquisition-platform distribution cross-tabulated against unit and split; preprocessing fitted on training partition only |
| G6 | Split locked | Split definition hashed and committed before any model is fit; per-split counts; test partition access-controlled |
| G7–G13 | Model and evaluation | Per proposal §§11–20 and `SECTIONS.md` |

### Independent verification

Where the prompt calls for validation by an independent source, method,
implementation or reference, the opportunities here are: M1 counts recomputed
by a second script sharing no code path; M3 class assignment cross-checked
against the dataset publication, with disagreement recorded as conflict rather
than resolved in favour of either; M4 parsing validated against the published
nomenclature specification rather than our own pattern; peptide extraction
re-run on a sample of containers with a second reader implementation and
sequence sets compared exactly; metrics re-implemented independently on one
split and intervals compared. Each is recorded pass/fail with the comparison
artifact retained. Where independent verification is unavailable, that is
stated rather than omitted.

## Known methodological limitations

Standing limitations of the approach, distinct from open decisions. Carried
into `REPORT.md`.

1. **Participant-bounded resolution.** Every uncertainty statement about
   generalization is bounded by the number of independent participants, which
   is small and fixed. Confirmed empirically by run-001: bootstrap replicates
   are irrelevant across a 250-fold range, while participant count is not.
2. **Unit count versus split stability.** With few units a fixed split is
   unstable and grouped cross-validation reuses units across folds; neither
   resolves the other's weakness.
3. **Unbalanced contribution.** **Verified:** acquisitions per participant
   range 3 to 15 (29 units at 3, 17 at 5, a four-unit tail at 8/9/10/15). The
   heaviest unit contributes 5× the lightest, so pooled peptide-level
   statistics are dominated by a handful of units. This is why
   participant-level resampling is primary.
4. **Shared sequences are real.** Overlap between participants is expected, not
   artifact. Any split rule either permits a form of leakage or discards real
   signal; D003 chooses which, and the choice cannot be avoided.
5. **Platform confounding — confirmed total, not partial.** Two platforms
   split the class-I units 25/27 with **zero overlap**: no unit spans both
   (`QC_G3.md`). Platform and participant are therefore not separable by any
   split over participants. Stratification keeps the split from *becoming* a
   platform split but cannot make the effects separable. Formally accepted as
   a limitation under D005.
6. **Negative-class dependence.** All performance figures are statements about
   discrimination against a constructed comparison class. They do not transfer
   across constructions and are not comparable to published numbers built on
   different ones.
7. **Absence is not negative evidence.** Non-observation reflects both genuine
   absence and detection limits. A hard-negative construction inherits this and
   cannot resolve it.
8. **Closed comparison sets.** Where M7 returns `UNVERIFIABLE`, the fairness of
   the §18 comparison is unestablished in an unknown direction.
9. **Metadata is the ceiling.** Phase A asserts only what the deposited
   annotation asserts. An error in the source annotation propagates through
   every mapping and is undetectable from inside this pipeline, except where
   independent verification happens to cover it.
10. **Metric bias at extreme class ratio.** Established by run-001: average
    precision is biased upward at severe imbalance, and the bias exceeds
    interval width as a source of miscoverage. Not fixable by resampling.

## Execution order

No stage begins before its predecessor's gate passes. Named decisions in
brackets must be RESOLVED before the stage they annotate executes.

```
S1  retrieve manifest + metadata, checksum          -> G1   [D013]
S2  M1  file to row                                 -> G1
S3  M3  class assignment                            -> G2
S4  M4  genotype parse                              -> G2   [D001, D012]
S5  M2  unit resolution                             -> G3   [D011]
S6  M5  container to run                            -> G3
S7  retrieve containers, stream-extract peptides    -> G3
S8  M6  peptide to unit, freeze filtering           -> G4   [D004, D007]
S9  negative construction, fix class ratio          -> G4   [D002]
S10 leakage + confound audit                        -> G5   [D003, D005]
S11 split construction, hash and commit             -> G6
S12 preregistration freeze                          -> G6   [D008, D009, D010]
S13 model fit                                       -> G7-G10
S14 held-out evaluation, resampling                 -> G10-G12
S15 M7 contamination check, comparison              -> G11  [D006]
S16 interpretation, report, clean re-run            -> G13
```

S1–S7 are solvable from metadata and are blocked only by retrieval. S8 onward
is additionally blocked until the dataset-definition decisions close.

## Outputs

| Artifact | Stage | Mapping |
|---|---|---|
| `FILE_MAP.csv`, `FILE_MAP_REJECTS.csv` | S2 | M1 |
| `ELIGIBILITY.csv` | S3 | M3 |
| `UNIT_GENOTYPE.csv` | S4 | M4 |
| `UNITS.csv` | S5 | M2 |
| `CONTAINER_RUN_MAP.csv` | S6 | M5 |
| `PEPTIDE_OBSERVATIONS.parquet` | S7–S8 | M6 |
| `POSITIVES.csv`, `NEGATIVES.csv` | S8–S9 | M6 |
| `TRAIN.csv`, `VALIDATION.csv`, `TEST.csv` | S11 | — |
| `QC_G*.md` | each gate | — |

Every output carries a unique identifier, its generating script and commit, its
input checksums, and a caption stating what it shows and what it does not.
Rejected and failed outputs are retained with the reason for rejection.

## See also

`PROJECT_PROMPT.md` (governing) · `PXD024871_CNN_Experiment_Proposal.md` ·
`SECTIONS.md` · `DECISION_LOG.md` · `DATA_SOURCES.md` · `FLOWCHART.md` ·
`REPORT.md` · `POWER_ANALYSIS.md`
