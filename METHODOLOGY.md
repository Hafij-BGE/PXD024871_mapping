# METHODOLOGY

Mapping methodology for PXD024871. Written before execution; this document is
the specification, not a report of what happened.

**Status:** OPEN — specification drafted, no mapping executed.
**Governing rules:** no raw data is modified; no ambiguous match is silently
forced; every mapping decision is traceable to the evidence that produced it.

Numbers appearing in this document that originate from external metadata
descriptions are marked **[provisional]** and are not treated as established
until recomputed from retrieved files and recorded in `DATA_SOURCES.md`.

---

## 1. What is being mapped

The project resolves a deposited proteomics submission into an analysis-ready
peptide table whose every row carries a complete provenance chain back to a
deposited file. The pipeline is a chain of seven distinct joins, each with its
own failure modes. They are specified separately below because a single
"mapping" abstraction would hide the places where evidence is weak.

```
deposited accession
  → file manifest                      M1 ─ file ↔ metadata row
  → sample metadata rows               M2 ─ row  → biological unit
                                       M3 ─ row  → enrichment class
                                       M4 ─ unit → genotype
  → identification containers          M5 ─ container → run
  → peptide identifications            M6 ─ peptide → biological unit
  → analysis peptide table             M7 ─ peptide → external predictor sets
```

M1–M5 are provenance mapping (Phase A). M6 produces the analysis table
(Phase B). M7 serves the comparison in proposal §18 and exists to detect
contamination, not to produce data.

### Scope boundary

The CNN defined in the proposal is **downstream of all seven mappings** and is
never an input to any of them. No model output may be used to assign a file to
a class, a run to a unit, or a peptide to a donor. This restates proposal §1
and §28 as an operational constraint: any code path from a model artifact back
into the mapping tables is a defect.

---

## 2. Global status vocabulary

One vocabulary is used across all mappings so that confidence composes along
the chain. Per-mapping meanings are given in each section.

| Status | Meaning | Eligible for analysis |
|---|---|---|
| `EXACT` | Deterministic match on a normalized key; one source, one target | Yes |
| `EVIDENCED` | Resolved from an explicit metadata assertion, not a key join | Yes |
| `PARTIAL` | Resolved, but the evidence is known incomplete | Yes, flagged |
| `AMBIGUOUS` | Two or more defensible targets; none selected | No |
| `UNMATCHED` | No target found | No |
| `OUT_OF_SCOPE` | No target expected; not a failure | n/a |
| `CONFLICT` | Two evidence sources disagree | No |

`AMBIGUOUS`, `UNMATCHED` and `CONFLICT` rows are written to a rejects file with
the reason and the candidate set. They are never dropped, and never resolved by
picking the first, closest, or most plausible candidate.

### Composition rule

A derived row's status is the **weakest** status along its provenance chain.
A peptide joined through an `EXACT` file match, an `EVIDENCED` class
assignment, and a `PARTIAL` genotype is `PARTIAL`. Weakening is monotonic: no
downstream step may upgrade a status.

---

## 3. Normalization rules

Applied identically wherever a key is compared. Normalization is for comparison
only; the original value is retained verbatim in a `*_raw` column alongside
every normalized key.

| Rule | Specification |
|---|---|
| N1 Unicode | Normalize to NFC before any comparison |
| N2 Whitespace | Strip leading/trailing; collapse internal runs to one space |
| N3 Case | Case-fold for comparison; never alter the stored original |
| N4 Path | Strip directory components; compare basename only |
| N5 Extension | Retain; extension is part of file identity |
| N6 Delimiters | Split multi-value metadata fields on the delimiter observed in the file, recorded per field; never on a guessed delimiter |
| N7 Empty | Distinguish absent, empty string, and sentinel values; all three map to `UNMATCHED`, with the distinction recorded |
| N8 Numeric identifiers | Compared as strings. Leading zeros are significant and are never stripped |

N8 matters: identifiers differing only by leading zeros or by a single digit are
distinct entities, and numeric coercion silently merges them.

---

## 4. Approximate matching policy

**Fuzzy matching is not permitted on any identifier join in this project.**

This is a deliberate departure from the master prompt's general allowance for
approximate matching, and the reason is specific to this data: the identifier
space is dense in near-neighbours. Run filenames differ by one character
between genuinely different acquisitions; participant identifiers differ by one
digit between different individuals. Any edit-distance threshold loose enough
to repair a real typo is also loose enough to merge two distinct entities, and
the merge is silent and unrecoverable downstream.

Consequence: every join is exact-or-nothing, and the unmatched set is expected
to be non-empty. A non-empty unmatched set is a normal outcome to be reported,
not a failure to be eliminated by loosening the match.

Where a near-miss is observed, it is recorded in the rejects file **as a
candidate for human adjudication**, with the normalized keys of both sides and
the edit distance, and it remains `UNMATCHED` until adjudicated. Adjudication,
if it happens, is a logged decision in `DECISION_LOG.md`, not a code change to
the matcher.

---

## 5. Mapping specifications

### M1 — Deposited file ↔ metadata row

| Field | Specification |
|---|---|
| Source entity | Deposited filename, from the repository file manifest |
| Target entity | Sample-metadata row, keyed on its data-file reference column |
| Matching criteria | Equality of normalized basename after N1–N5 |
| Normalization | N1–N5, N8 |
| Exact rule | One manifest filename ↔ exactly one metadata row |
| Approximate rule | Prohibited (§4) |
| Expected cardinality | 1:1 over the acquisition files; **[provisional]** the manifest is described as holding ~402 acquisition files against ~402 metadata rows |
| `OUT_OF_SCOPE` | Identification containers and the metadata file itself appear in the manifest and have no metadata row of their own. They are classified `OUT_OF_SCOPE`, not `UNMATCHED`, and are enumerated explicitly so the category cannot absorb a genuine failure |
| `AMBIGUOUS` | One row referencing ≥2 manifest files, or one file matched by ≥2 rows |
| `UNMATCHED` | Acquisition file with no row, or row referencing a file absent from the manifest. Both directions are reported separately |
| Duplicates | Manifest filenames must be unique after normalization. A collision is `CONFLICT` and blocks the gate — it means two deposited files normalize to one key |
| Output | `FILE_MAP.csv`, `FILE_MAP_REJECTS.csv` |
| Gate | G1 |

Both join directions are reported. A left-only count is not evidence of
completeness.

### M2 — Metadata row → biological unit

| Field | Specification |
|---|---|
| Source entity | Metadata row attributes: participant identifier, biological replicate, technical replicate, fraction identifier |
| Target entity | `unit_id`, the independent unit for splitting and resampling |
| Matching criteria | `unit_id` is derived from the participant identifier alone |
| Normalization | N1–N3, N7, N8 |
| Nesting rule | Replicates and fractions are **attributes within** a unit, not units. Multiple rows mapping to one `unit_id` is the expected case |
| `UNMATCHED` | Row with absent participant identifier. Not inferred from filename, acquisition order, or position in the file |
| `CONFLICT` | Rows sharing a participant identifier but carrying contradictory unit-level attributes |
| Duplicates | Expected and retained; counted per unit |
| Output | `UNITS.csv` with run/replicate/fraction counts per unit |
| Gate | G3 |

**This definition is a forced choice, not a fact.** Treating the participant as
the unit asserts that replicates and fractions are not independent
observations. That is the defensible reading, and it is also the conservative
one — it yields the smallest unit count and therefore the widest uncertainty
intervals. The alternative, treating replicates as units, would inflate the
apparent sample size and narrow intervals around a statistic whose real
resolution is set by participant count. Logged as a pending decision
(`DECISION_LOG` D011) so the choice is on the record rather than embedded in
code.

Downstream consequence: the resampling unit in proposal §16 is `unit_id`, and
the bootstrap's effective resolution is bounded by the number of units, not by
the number of peptides and not by B.

### M3 — Metadata row → enrichment class

| Field | Specification |
|---|---|
| Source entity | The row's enrichment-reagent annotation |
| Target entity | `hla_class` ∈ {`I`, `II`, `UNKNOWN`} |
| Matching criteria | Controlled-vocabulary lookup against an explicit, version-controlled term table |
| Normalization | N1–N3, N6 |
| Exact rule | Enumerate the distinct reagent strings present in the file **first**; map each one deliberately in `vocab/enrichment_class.tsv`; a string absent from the table raises an error and halts the stage |
| Approximate rule | Prohibited. Substring and keyword matching on reagent names is specifically excluded — a term table is small, auditable, and cannot silently misclassify |
| `AMBIGUOUS` | A row annotating reagents that map to more than one class |
| `UNKNOWN` | Reagent annotation absent or unmappable → excluded from the eligible set |
| Evidence requirement | Class is `EVIDENCED` from the depositor's annotation only. **Filename-derived class assignment is prohibited** (proposal §5 A2) |
| Output | `hla_class` and `source_evidence` columns in `FILE_MAP.csv`; `ELIGIBILITY.csv` |
| Gate | G2 |

`source_evidence` records the literal annotation string that produced the
assignment, so every class label is auditable to its source cell without
re-reading the metadata file.

**[provisional]** The reagent annotation is described as partitioning the
acquisitions cleanly by class. If true, this mapping is `EVIDENCED` for every
row and no inference is needed. That claim is checked at G2 by enumerating the
distinct values and their row counts — not assumed.

### M4 — Biological unit → genotype

| Field | Specification |
|---|---|
| Source entity | Per-participant typing annotation, free text |
| Target entity | Normalized allele set per `unit_id` |
| Matching criteria | Parse → validate → canonicalize to two-field resolution |
| Normalization | N1–N3, N6, then nomenclature canonicalization |
| Validation | Each token must match the standard nomenclature pattern for a two-field allele designation. Tokens failing validation are retained verbatim and flagged, never discarded and never repaired |
| `PARTIAL` | Fewer loci resolved than the expected complement |
| `LOW_RESOLUTION` | Token below two-field resolution, or carrying an ambiguity code → retained, flagged, excluded from allele-stratified analyses |
| `ABSENT` | No typing annotation for the unit |
| Output | `UNIT_GENOTYPE.csv`; allele-frequency table |
| Gate | G2 |

**Imputation is prohibited.** A unit with fewer recorded alleles than loci is
indistinguishable, from this metadata alone, between a genuine single-allele
locus and incomplete reporting. Both are real and the metadata does not
separate them. Filling the gap by duplicating the observed allele would
manufacture an assertion the source does not make. Such units are `PARTIAL`,
usable for participant-level analysis, excluded from any analysis keyed on the
complete allele complement. Logged as pending decision D012.

**Why this mapping exists at all:** it is the evidence base for `DECISION_LOG`
D001. Without it, the proposal's §25 generalization claim cannot be
distinguished from a claim about participant-level batch independence. The
allele-frequency table produced here is also what determines whether an
allele-disjoint split is constructible — if the common alleles are shared
across most units, it is not, and the claim must be weakened instead.

### M5 — Identification container → acquisition run

| Field | Specification |
|---|---|
| Source entity | Identification container file |
| Target entity | One or more acquisition runs |
| Matching criteria | Read the container's own internal record of its input spectrum files; join those on normalized basename to `FILE_MAP.csv` |
| Normalization | N1–N5 |
| Exact rule | Resolution is from the container's internal table. Filename-pattern inference is a flagged fallback, not the primary path |
| Expected cardinality | Not 1:1. **[provisional]** containers are described as fewer in number than acquisitions, implying aggregation; the true fan-out is read from the files |
| `AMBIGUOUS` | Internal reference resolving to ≥2 manifest files |
| `UNMATCHED` | Internal reference to a file absent from the manifest → recorded; peptides from that reference are not assigned a unit |
| Status | `EXACT` via internal record; `PARTIAL` via filename fallback; `UNMATCHED` otherwise |
| Output | `CONTAINER_RUN_MAP.csv` |
| Gate | G3 |

Reading the internal table rather than parsing filenames is the difference
between `EXACT` and `PARTIAL` for every peptide downstream, because M6 inherits
this status.

### M6 — Peptide identification → biological unit

Composite mapping; it introduces no new join, only composition and filtering.

| Field | Specification |
|---|---|
| Chain | peptide → container (M5) → run → metadata row (M1) → unit (M2), with class (M3) and genotype (M4) attached |
| Status | Weakest status in the chain (§2) |
| Filtering | Eligibility and quality thresholds frozen before any model evaluation (proposal §6). Threshold selection is `DECISION_LOG` D004 |
| Duplicate handling | A sequence observed in multiple runs or units is **not** deduplicated at this stage. The full observation table is retained with one row per observation, and unique-sequence collapse happens later and separately, because the collapse rule depends on D003 |
| Provenance columns | Every row carries container, run, metadata row, unit, class, genotype, and the status of each link |
| Output | `PEPTIDE_OBSERVATIONS.parquet` → `POSITIVES.csv` |
| Gate | G4 |

Retaining observations rather than collapsing early is what makes D003
answerable: the cross-unit sharing structure is only visible before collapse,
and it is the input to deciding how shared sequences are split.

### M7 — Peptide → external predictor training sets

Exists to detect contamination in the proposal §18 comparison, which is
otherwise unfair in an unknown direction.

| Field | Specification |
|---|---|
| Source entity | Analysis-table sequence |
| Target entity | Membership in each comparison predictor's training data |
| Matching criteria | Exact normalized sequence equality |
| Approximate rule | Prohibited |
| Output | Per-predictor overlap count and the overlapping sequence list |
| `UNVERIFIABLE` | Where a predictor's training set is not obtainable, overlap **cannot be excluded**. This is recorded as a stated limitation on the comparison, not passed as a clean check |
| Gate | G11 |

The `UNVERIFIABLE` category is the point of this mapping. A comparison against
a predictor whose training data cannot be inspected is reportable only with
that caveat attached; silently treating it as uncontaminated would overstate
the CNN's disadvantage or advantage without knowing which.

---

## 6. Traceability record

Per master prompt §8, every executed stage records this chain. Satisfied by one
row per stage in `RUN_LOG.md` plus the referenced artifacts.

| Element | Where recorded |
|---|---|
| What was done | Stage identifier and title |
| Why | Purpose, and the `SECTIONS.md` section it serves |
| Method | The M-number above, and the vocabulary/term-table version used |
| Code | Script path and content hash |
| Environment | Interpreter and library versions; `ENVIRONMENT.md` |
| Input | Path and checksum of every input |
| Parameters | Full parameter set, including thresholds and seed |
| Output | Path and checksum of every output |
| QC | Gate identifier, the checks run, pass/fail per check |
| Interpretation | What the result means, and what it blocks or unblocks |

A stage whose inputs, code, and parameters are all recorded with checksums is
re-runnable from this record alone. That is the reproducibility criterion: not
that the stage ran, but that it can be re-run from the documentation without
consulting the person who ran it.

---

## 7. QC gates

Each gate is a named set of checks with recorded pass/fail per check. A FAIL
blocks progression until corrected, or until formally accepted as a limitation
by a logged decision. A gate is never partially passed.

| Gate | Stage | Checks |
|---|---|---|
| G1 | Retrieval & inventory | Every retrieved file has a recorded checksum; published checksums verified where available; manifest count matches retrieval count; M1 join reported in both directions; `OUT_OF_SCOPE` set enumerated explicitly |
| G2 | Class & genotype | Reagent vocabulary complete, no unmapped term; class counts reported per distinct term; genotype parse rate and failure list; allele frequency across units computed; typing completeness per unit |
| G3 | Units & containers | Every eligible row assigned a unit; unit count and per-unit run counts reported; container fan-out read from internal records; unassignable peptide sources listed |
| G4 | Peptide table frozen | Length distribution within the declared range; threshold applied as preregistered; cross-unit sharing structure quantified; positive/negative overlap empty; class ratio fixed and recorded; minimum-N gate evaluated |
| G5 | Leakage & confounds | No sequence crosses splits except as D003 permits; no unit crosses splits; acquisition-platform distribution cross-tabulated against unit and against split; preprocessing fitted on training partition only |
| G6 | Split locked | Split definition hashed and committed before any model is fit; per-split counts reported; test partition access-controlled |
| G7–G13 | Model and evaluation | Per proposal §§11–20 and `SECTIONS.md` |

### Independent verification

Where the master prompt calls for validation by an independent source or
implementation, the opportunities in this project are:

- **M1 counts** — recomputed from the raw manifest by a second script with no
  shared code path with the first.
- **M3 class assignment** — cross-checked against the dataset's accompanying
  publication description; a disagreement is `CONFLICT`, not a tie broken in
  favour of either source.
- **M4 parsing** — validated against the published nomenclature specification
  rather than against our own regex.
- **Peptide extraction** — a sample of containers re-extracted with a second
  reader implementation; sequence sets compared exactly.
- **Metrics** — bootstrap re-implemented independently of the existing project
  framework on one split, and the intervals compared.

Each is recorded as pass/fail with the comparison artifact retained. Where
independent verification is not available, that is stated rather than omitted.

---

## 8. Known methodological limitations

Standing limitations of the approach itself, distinct from open decisions.
Carried into the limitations section of the final report.

1. **Participant-bounded resolution.** Every uncertainty statement about
   generalization is bounded by the number of independent participants, which
   is small and fixed. No resampling procedure and no choice of B increases it.
2. **Unit count versus split stability.** With few units, a fixed split is
   unstable and grouped cross-validation reuses units across folds; neither
   fully resolves the other's weakness.
3. **Unbalanced contribution.** **[provisional]** acquisition counts per
   participant are described as varying several-fold. Pooled peptide-level
   statistics are therefore dominated by the heaviest-contributing
   participants, which is why participant-level resampling is primary and
   pooled peptide-level numbers are secondary.
4. **Shared sequences are biologically real.** Overlap between participants is
   expected, not an artifact. Any split rule either permits a form of leakage
   or discards real signal; D003 chooses which, and the choice cannot be
   avoided.
5. **Acquisition-platform confounding.** **[provisional]** more than one
   platform is described across the acquisitions. If platform correlates with
   participant, platform and participant effects are not separable by any split
   over participants. G5 quantifies the correlation; it cannot remove it.
6. **Negative-class dependence.** All performance metrics are statements about
   discrimination against a constructed comparison class. They do not transfer
   across negative-set constructions, and are not comparable to published
   numbers built on different ones.
7. **Absence is not negative evidence.** Non-observation reflects both genuine
   absence and the detection limits of the acquisition. A hard-negative
   construction built on non-observation inherits this and cannot resolve it.
8. **Closed comparison sets.** Where M7 returns `UNVERIFIABLE`, the fairness of
   the §18 comparison is unestablished in an unknown direction.
9. **Metadata is the ceiling.** Phase A asserts only what the deposited
   annotation asserts. An error in the source annotation propagates through
   every mapping and is undetectable from within this pipeline, except where
   independent verification (§7) happens to cover it.

---

## 9. Execution order

No stage begins before its predecessor's gate passes.

```
S1  retrieve manifest + metadata, checksum          → G1
S2  M1  file ↔ row                                  → G1
S3  M3  class assignment          ┐
S4  M4  genotype parse            ┘                 → G2   [D001]
S5  M2  unit resolution                             → G3
S6  M5  container → run                             → G3
S7  retrieve containers, stream-extract peptides    → G3
S8  M6  peptide → unit, freeze filtering            → G4   [D004, D007]
S9  negative construction, fix class ratio          → G4   [D002]
S10 leakage + confound audit                        → G5   [D003, D005]
S11 split construction, hash and commit             → G6
S12 preregistration freeze                          → G6   [D008, D009, D010]
S13 model fit                                       → G7–G10
S14 held-out evaluation, resampling                 → G10–G12
S15 M7 contamination check, comparison              → G11  [D006]
S16 interpretation, report, clean re-run            → G13
```

S1–S7 are substantially solvable from the deposited metadata and do not depend
on any open decision except D001 at G2. S8 onward is blocked until the dataset
definition decisions close.

Named decisions in brackets must be `RESOLVED` in `DECISION_LOG.md` before the
stage they annotate executes.

---

## 10. Outputs

| Artifact | Produced by | Mapping |
|---|---|---|
| `DATA_SOURCES.md` | S1 | — |
| `FILE_MAP.csv` | S2 | M1 |
| `FILE_MAP_REJECTS.csv` | S2 | M1 |
| `ELIGIBILITY.csv` | S3 | M3 |
| `UNIT_GENOTYPE.csv` | S4 | M4 |
| `UNITS.csv` | S5 | M2 |
| `CONTAINER_RUN_MAP.csv` | S6 | M5 |
| `PEPTIDE_OBSERVATIONS.parquet` | S7–S8 | M6 |
| `POSITIVES.csv`, `NEGATIVES.csv` | S8–S9 | M6 |
| `TRAIN.csv`, `VALIDATION.csv`, `TEST.csv` | S11 | — |
| `QC_G*.md` | each gate | — |
| `RUN_LOG.md`, `ENVIRONMENT.md` | every stage | — |

Every output carries a unique identifier, its generating script and commit, its
input checksums, and a caption stating what it shows and what it does not.
Rejected and failed outputs are retained with the reason for rejection.

---

## See also

- `PXD024871_CNN_Experiment_Proposal.md` — the experiment this serves
- `SECTIONS.md` — per-section status and gate schedule
- `DECISION_LOG.md` — open decisions blocking gates
- `DATA_SOURCES.md` — source provenance registry
- `FLOWCHART.md` — diagrammatic view of this specification
