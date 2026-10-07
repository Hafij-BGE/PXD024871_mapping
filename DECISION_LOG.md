# DECISION_LOG

Methodological decisions for the PXD024871 CNN experiment. Append-only.
Each entry is traceable: what was decided, why, what it changes, who/when.

Status values: OPEN / RESOLVED / PERMANENT

---

## D001 — Carry HLA genotype into the dataset schema

**Date opened:** 2026-10-06 · **Resolved:** 2026-10-06 by run-003
**Status:** RESOLVED — option A taken; see *Resolved by Phase A retrieval* below
**Blocks:** nothing; G2 passed
**Affects sections:** §5 A2, §6, §9, §10, §25

**Question**
Should per-donor HLA genotype be a first-class column in the file map and the
peptide table, and should the evaluation design include an allele-disjoint
split alongside the donor-disjoint split?

**Why this is a blocker**
Class-I ligand sets are allele-specific. If genotype is not carried through,
a pooled model is fit to a mixture of allele-specific distributions, and
donor-held-out performance cannot separate allele mismatch from genuine
failure to generalize. The proposal's §5 A2 table has `hla_class` but no
allele field, so the current schema cannot support that separation.

**Evidence available**
The community-annotated SDRF reports `characteristics[mhc typing]` for the
class-I donors at 4-digit resolution. Typing completeness is uneven across
donors (some have fewer than six alleles recorded). Allele frequencies are
skewed — the most common allele appears in roughly half the class-I donors —
so a donor-disjoint split will almost always share alleles between train and
test. All of these numbers must be recomputed from the SDRF at G2 and
recorded; the figures quoted in discussion are not yet verified in-repo.

**Options**
- A — Add `hla_genotype` to the file map and peptide table; report
  donor-disjoint as primary and allele-disjoint as a preregistered secondary
  split.
- B — Add the column for provenance only; keep donor-disjoint as the sole
  design and weaken the §25 generalization claim accordingly.
- C — Omit genotype. Rejected on the reasoning above; recorded so the
  rejection is traceable.

**Recommendation:** A. It costs one join and makes the §25 claim testable
rather than merely stated.

**What must be true before this can be marked RESOLVED**
- Genotype parsed from the SDRF with a recorded normalization rule
  (delimiter, resolution, handling of partial typing).
- Donor and allele counts computed in-repo, not quoted.
- Secondary split either specified or explicitly declined, with the §25
  claim reworded to match.

**Next step:** Parse the SDRF typing field, compute completeness per donor,
then choose A or B on that evidence.

---

## D002 — Negative controls · RESOLVED

**Opened:** 2026-10-06 · **Resolved:** 2026-10-06 · **Status:** RESOLVED
**Evidence:** run-008, `results/qc/negative_diagnostic.json`; run-001 F4/F6; run-006

**Decision: primary negatives are set C — length-matched peptides drawn from
proteins that did yield observed peptides, excluding anything observed. Class
ratio 1:1. Set B, shuffled positives, is preregistered as a secondary control
reported alongside.**

### The diagnostic that decided it

I committed when opening this to choosing on a composition diagnostic run before
training, and to preferring the construction not separable on composition alone.
The optimal *linear* classifier on 20-dimensional amino-acid composition, no
positional information, held out:

| Set | Construction | Composition-only AUROC | Composition divergence |
|---|---|---|---|
| A | reference-derived, length-matched | 0.6120 | 10.05 pp |
| B | shuffled positives | **0.5000** | 0.00 pp |
| C | same source proteins, unobserved | 0.6085 | 10.26 pp |

### The criterion I set turned out to be insufficient, and I am not applying it

Read literally, B wins: it leaks exactly nothing, by construction, since
shuffling preserves composition. But B is not a set of biologically possible
non-ligands — shuffled peptides are not peptides any cell could present. A model
separating real fragments from shuffled ones can succeed on *sequence realism*
alone, which every real protein fragment has and no shuffled string does, while
learning nothing about presentation.

So the original criterion optimises for the wrong thing when followed to its
conclusion. A set can be unleakable on composition and still pose a question
nobody asked.

### Why C is primary

C is the biologically meaningful contrast: real peptides from proteins the
sample demonstrably expressed, which were nonetheless not observed. That
controls for expression — A would let the model learn which proteins are present
in the sample rather than which peptides are presented from them — and its
composition leakage is indistinguishable from A's (0.6085 vs 0.6120), so the
control costs nothing on the criterion that motivated the diagnostic.

### The leakage is declared, not eliminated

**The floor for the primary endpoint is not chance.** A composition-only linear
model reaches AUROC 0.6085 against set C, which at 1:1 corresponds to an
average precision of **0.597** under the binormal model, not 0.5 — so nearly a
fifth of the distance from chance to a perfect score is available before the
CNN learns anything. Any reported AP must be stated
against that floor, and `results/qc/negative_diagnostic.json` is its source.

This **amends D008**, which specified a lift over prevalence. Prevalence is the
wrong reference: it describes a model with no information, and we have measured
that a trivial one does considerably better. The threshold must be a lift over
the measured composition floor.

### Set B's role

Reported as a secondary control, not an alternative. The pairing is
diagnostic: strong on C and weak on B would mean the model found composition;
strong on both means it found positional structure, which is what the experiment
claims to test. Neither reading is available from one set alone.

### Class ratio 1:1

Three independent grounds converge, which is worth more than any one:
run-001 F4 (average precision is biased upward at wide ratios, by roughly 10% of
the lift at 1:100), F6 (relative precision degrades 3–5× at 1:100), and run-006
(the ratio is a 5.5× compute lever). With D024's cap this gives 520,000
positives and 520,000 negatives.

### Rejected, retained with reasons

**Set A** — composition leakage equal to C's with no expression control, so it
is strictly dominated. **Set B as primary** — argued above. **1:10 and 1:100** —
rejected on F4, F6 and compute together.

### Residual limitation, not solved

Non-observation is not non-presentation. Set C's members may well be presented
and simply not detected: run-006 measured 1.45× redundancy with the final unit
still 55% novel, so these repertoires are deeply undersampled. The negative
class is therefore contaminated at an unknown rate, which biases measured
performance downward. This is inherent to any construction built on absence,
survives into the report, and is the reason §20's interpretation cannot treat a
negative label as evidence of non-presentation.

---

## Pending — not yet written up as entries

Raised in review, still unlogged. Each needs its own entry before the gate it
blocks:

| # | Decision | Blocks |
|---|---|---|
| D021 | Peak extraction disk corrected from ~2 GB to ~12 GiB once container sizes were verified. **RESOLVED** — see entry below | G8 |
| D022 | Compute gate resized: planning worst case 100k -> 2M positives, cap 48h -> 96h, class ratio 1:1. **RESOLVED**, but flags that the budget is not executable on this hardware. See entry below | G8 |
| D023 | Provenance cannot depend on the downloader surviving: a completed transfer whose writer died left an unrecorded, truncated file. **RESOLVED** — reconciler added. See entry below | G1 |
| D026 | Architecture, input representation and training protocol frozen. Closes the preregistration gap found while writing Methods: these were carried past the freeze unlocked. See entry below | before training |
| D027 | How the 25 final models yield one endpoint value. §13 required all 25 be reported but never said how they combine. **RESOLVED before the test partition was read.** See entry below | before --mode test |
| D028 | Cross-platform transfer design: D025 run as preregistered, plus a matched within-platform control, because the preregistered form alone confounds platform with training-set size. Logged before the run. See entry below | before transfer |
| D029 | The `allele_disjoint_partition` split holds out ONE allele, not a disjoint set: only 5 of 36 test alleles are absent from training and 21.7% of a test unit's repertoire is unseen, so the design is attenuated ~5x. D001 run verbatim, renamed dominant-allele-held-out, plus a matched pair and a validated allele-enriched stratum. Logged before the run | before G13 |
| D030 | The D029 allele stratum was defined as "in M_AM's pool, not in M_AD's", so M_AM had memorised 97.93% of it and M_AD 0.00%. Its +0.0660 is void; corrected to +0.0335 on row sets neither arm saw. Second instance of the TEST_LEAKFREE failure mode, so a standing check is added | voids a result |
| D031 | Multi-allele test preregistered: five-allele replication plus the one symmetric allele PAIR (A*02:01 vs C*07:02), where a sign reversal between the two exclusive strata is the signature D029's contrast II could not deliver. Also finds that PARTIAL typing under-reports a locus, so 2 of D001's 23 non-carriers are not certain | may release G13 |
| D032 | **ACCEPTED by the project owner, 2026-10-07.** G13's D031 criterion required both Part B directions to be significant; the 6-unit C*07:02 arm could not supply that. Narrowed to one direction. **G13 RELEASED, §20 written to the accepted wording** | G13 passed |
| D033 | §18 admission executed under D006. Both MHCflurry lines are quantified `OVERLAPPING` (8.29% / 9.11% of test positives, 6.9:1 and 7.9:1 biased toward positives). D006 was wrong in three helpful ways: GitHub release assets are reachable, each model bundle ships its own training data, and both lines are admissible. Primary comparison subset must be naive to BOTH systems, not just the predictor | G11 |
| D034 | Final freeze. `scripts/freeze.py --write` refuses to write a manifest unless eight verification checks pass first, so the record exists only because the tree was checked. 348 files, 93.9 MB. Tag refused again, as in D009; the commit is the anchor | closes the project |
| D003 | Cross-split sequence leakage. **RESOLVED** — keep shared sequences, report the leakage-free subset as a sensitivity analysis. 14.59% of test positives are seen in training under unit-disjoint splitting. See entry below | G5, G6 |
| D004 | Confidence threshold. **RESOLVED as a no-op** — 99.29% of the union is at the top level, so re-filtering removes 0.7%. Must be re-framed around the PeptideScores table if purity control is wanted | G4 |
| D024 | Per-unit positive cap. **RESOLVED: 10,000 per unit, length-stratified, seed 20261006.** Chosen from a precision curve; costs 0.16% of attainable precision | G4, G6 |
| D025 | Platform stratification and cross-platform transfer. **RESOLVED** — stratification mandatory; transfer analysis preregistered. Instrument is learnable from composition at AUROC 0.645 vs 0.515 control. See entry below | G6 |
| D005 | Instrument confound. **RESOLVED — accepted as a limitation**; total confound, cannot be corrected. See entry below | G3, FAIL accepted |
| D006 | Predictor training-set overlap. **RESOLVED as a protocol**: no predictor enters §18 without its training list obtained; handling fixed per outcome; §18 may never be promoted while any predictor is UNVERIFIABLE. See entry below | G11 |
| D007 | Minimum-N gate. **RESOLVED — clears overwhelmingly**: 2,658,972 eligible positives. The confirmatory arm is not data-limited | G4 |
| D008 | Decision rule for §25. **RESOLVED: reject if the lower bound of a nominal-99% cluster-bootstrap interval exceeds 0.647** (floor 0.597 + 0.05). Nominal 99% because 95% delivers only ~89% actual coverage. See entry below | closed |
| D009 | Preregistration freeze. **RESOLVED** — the freeze commit is the anchor; `PREREGISTRATION.md` committed at it carries every artifact checksum. Tag attempted and refused by the remote; recorded rather than pretended. See entry below | G6 |
| D010 | Seed convention. **RESOLVED** — base 20261006 kept, per-purpose seeds derived via `scripts/seeds.py`; seed shopping prohibited. See entry below | G6 |
| D011 | Unit definition. **RESOLVED** — participant as unit; 52 class-I units over 222 runs, verified. See entry below | G3 passed |
| D012 | Partial typing. **RESOLVED** — 14 of 52 units partial, none imputed. See entry below | G2 passed |
| D013 | S2 route. **RESOLVED** — the metadata file is in the submission. See entry below | G1 passed |
| D014 | Primary endpoint: §25 kept, threshold raised; §18 preregistered secondary. **RATIFIED, RESOLVED** — see entry below. Contingent on D006 | constrains D008 |
| D020 | Compute gate numbers set from measured throughput on the target machine. **RESOLVED** — see entry below | G8 |
| D015 | Master prompt transcription. **CONFIRMED, RESOLVED** — see entry below | closed |
| D016 | Approximate matching prohibited on every identifier join. **RATIFIED, PERMANENT** — see entry below | standing rule |
| D017 | Proceeding with run-001 while G1 was failing. **RATIFIED, RESOLVED** — see entry below | closed |
| D018 | Required field sets omitted from `SECTIONS.md` and `RUN_LOG.md`, then repaired. **RATIFIED, RESOLVED** — see entry below | closed |
| D019 | `METHODOLOGY.md` restructured to the prompt's eleven-field format. **RATIFIED, PERMANENT** — see entry below | standing structure |

---

## D014 — Primary endpoint: keep §25, raised

**Date opened:** 2026-10-06 · **Date resolved:** 2026-10-06
**Status:** RESOLVED — **ratified by the author in session, 2026-10-06**
**Blocks:** nothing further; now constrains D008
**Not PERMANENT:** contingent on D006, see *Conditional* below
**Evidence:** run-001; `POWER_ANALYSIS.md` F1, F7; `METHODOLOGY.md` M7

**Question.** Should the §18 paired predictor comparison replace the §25
absolute claim as the confirmatory endpoint?

**Recommendation: keep §25 primary with a raised threshold; report §18 as the
better-powered secondary.**

**This reverses my own earlier lean, and the reason matters.** I opened D014 on
power grounds alone, where §18 plainly wins: its minimum detectable difference
is about 0.05 AP at ten held-out participants, while §25 as worded passes for a
classifier at AUROC 0.60 (F1, F7). Power is not the only consideration, and the
one I had not weighed is in M7.

**The deciding argument.** The two endpoints fail in different ways, and only
one failure is fixable:

- §25's weakness is **specification**. It has no threshold. That is repaired by
  writing one (D008), today, from numbers run-001 already produced.
- §18's weakness is **an unverifiable dependency**. Its fairness rests on the
  comparison predictors' training sets not containing these peptides, and M7
  returns `UNVERIFIABLE` wherever a training set cannot be obtained. Nothing in
  this project can resolve that. Making it confirmatory would rest the headline
  claim on an assumption we have no means to check, in a direction we could not
  even determine — contamination would flatter the existing predictors, making
  the CNN look worse, but we could not say by how much or whether it occurred.

A well-specified weaker claim beats a better-powered claim with an uncheckable
premise. Statistical power is worth less than knowing what you measured.

**Conditional on D006.** If the comparison predictors' training sets turn out to
be inspectable and M7 returns `CLEAN` or a quantified `OVERLAPPING`, the
objection disappears and §18 becomes the better endpoint on power grounds.
Revisit then; this recommendation is contingent, not permanent.

**Binding consequences, now ratified.**

1. **D008 is constrained, not free.** The §25 decision rule must be a *lift
   over prevalence* with the test applied to the interval's lower bound. Its
   *form* is fixed here; its *magnitude* still depends on D002, because
   prevalence is set by the class ratio. D008 therefore cannot close before
   D002.
2. **§18 is preregistered as secondary**, with its own analysis plan, and is
   reported whatever §25 shows. Its better power is not a reason to promote it
   post hoc — doing so after seeing results would be endpoint switching.
3. **§16 reports the participant-level interval with the F3 coverage shortfall
   stated**, not as a bare 95% claim.
4. **Promotion of §18 later requires a new entry citing this one**, and is
   permitted only on the D006 condition below — never on the basis of §25
   having failed.

**Why this is not PERMANENT.** The decision rests on a fact that may change:
that M7 cannot verify the comparison predictors' training sets. If D006
establishes they are inspectable, the objection disappears and §18 becomes the
better endpoint on power grounds. That revisit is anticipated here, so it would
be a supersession rather than a reversal — but it must happen *before* results
are seen, or it is endpoint switching regardless of how well justified.

**Ratification note.** Ratified on the author's instruction. The reasoning
behind it is mine and reversed my own earlier position; the authority for
adopting it is theirs.

---

## Resolved by Phase A retrieval — D001, D005, D011, D012, D013, D021

Resolved 2026-10-06 by run-003 against the retrieved sources. Evidence:
`results/qc/QC_G1.md`–`QC_G3.md`, `data/derived/`.

### D001 — HLA genotype in the schema · RESOLVED

Option A taken: `hla_genotype`, `genotype_status` and `n_alleles` are columns in
`FILE_MAP.csv` and `UNITS.csv`, and `ALLELE_FREQUENCY.csv` is emitted.

**The question D001 existed to answer is settled, and favourably.** An
allele-disjoint split is **constructible**: the most common allele appears in 29
of 52 units (56%), so holding out its carriers leaves 23 for training — costly
but feasible. 46 distinct alleles across 52 units, all 52 typed, zero
nomenclature failures. §25's claim can therefore be *tested* rather than merely
weakened, which is what I could not promise when this was opened.

### D005 — Instrument confound · RESOLVED, accepted as a limitation

**Total, not partial.** Two platforms partition the 52 class-I units 25/27 with
**zero overlap**: no unit spans both. G3 records it as a FAIL. It cannot be
corrected — it is a property of the deposited data — so under the governing
prompt it is formally **accepted as a limitation**.

**Cost to the study.** A unit-disjoint split cannot separate unit effects from
platform effects. Any "generalizes to unseen units" result is equally consistent
with a claim about generalizing across acquisition platforms. §25 must be worded
to acknowledge this; no split over units rescues it.

**Required mitigation, which is not a fix.** Stratify so both platforms appear
in every partition — both groups are large enough. That stops the split
*becoming* a platform split. It cannot make the effects separable, because no
unit supplies within-unit platform variation.

**No covariate rescue exists.** age and sex are "not available" on every row;
disease and tissue are uniform across all 222 class-I runs. There is nothing to
adjust with.

### D011 — Unit definition · RESOLVED

Participant as the unit, replicates and fractions nested, as proposed. Verified:
**52 class-I units over 222 runs** (61 across the submission, 9 class-II only).
Runs per unit 3–15: 29 units at 3, 17 at 5, a four-unit tail at 8/9/10/15.

The conservative reading was right. The heaviest unit contributes five times the
lightest, so pooled peptide-level statistics would be dominated by a handful of
units — which is why run-001 resampled units rather than peptides.

### D012 — Partial typing · RESOLVED

Verified: **38 COMPLETE** at six alleles, **14 PARTIAL** (4 units at four
alleles, 10 at five), zero ABSENT, zero LOW_RESOLUTION. 27% partial is material.
None imputed. They stay eligible for unit-level analysis and are excluded from
analyses keyed on the complete complement. The ambiguity named when this was
opened is real and unresolvable from this metadata.

### D013 — S2 retrieval route · RESOLVED

**Route 1: it is in the submission.** The metadata file appears in the manifest
as the single EXPERIMENTAL DESIGN entry, 317,806 bytes, retrieved from the
submission's own path. The separate community-annotation repository was not
needed. One prediction held: it is the **only** file of 504 without a published
checksum, so its integrity rests on our own SHA-256 plus the manifest's declared
size, which the retrieved file matches exactly.

### D021 — Peak extraction disk corrected · RESOLVED

Opened and closed by the same retrieval, because it corrects my own error.
`DATA_SOURCES.md` and D020 claimed ~2 GB peak extraction disk. Container sizes
from the manifest: median 841 MiB, **maximum 9.25 GiB** — so peak working space
is ~12 GiB, a 6× understatement. The container set is **107.53 GiB**, not the
~47.8 GB carried as provisional, exceeding the allowance by 3.6× rather than
1.6×. Conclusions survive: 12 GiB fits in 30 GB and streaming remains mandatory.

**Logged rather than quietly amended** because the ~2 GB figure sat in a budget
table as though it were a measurement, was wrong by 6×, and nothing in the
repository would have caught it — no container had been measured. The class of
error is worth recording, not just the instance.

---

## D022 — Compute gate resized

**Resolved:** 2026-10-06 · **Status:** RESOLVED, with a flagged hardware blocker
**Evidence:** run-002 (throughput), run-004/005 (yield, redundancy)

**Why reopened.** The gate was sized at a 100,000-positive worst case, taken
from run-001's assumption of 40 positives per acquisition. Measurement gives
**~16,500 per acquisition** — 411× higher — and cross-unit redundancy of only
**2.9–6.2%**, so the union projects to **~1.9M** at 52 units. The original
figure was wrong by 19×.

**Resized.** Planning worst case 2,000,000 positives; wall clock 48 → 96 h;
assumed class ratio 1:10 → 1:1. Grid, configurations, folds, seeds and the
reduction ladder are unchanged.

**The class ratio turns out to be a 5.5× compute lever**, which is new input to
D002. run-001's F4 and F6 already argued against wide ratios on estimator bias
and relative precision; compute now agrees. 1:1 is preferred on three
independent grounds, and that convergence is worth more than any one of them.

**The conclusion that matters is not a number.** At 1:1 and 2M positives the
grid is ~90 hours, and the session container is ephemeral. Raising the cap makes
the budget arithmetically consistent; it does not make it executable. The work
has outgrown this environment, and the honest statement is that **a hardware
decision now gates the preregistration freeze** — a GPU being the option that
turns a marginal design into a comfortable one.

This also retires a run-002 conclusion. That run found no GPU was needed, which
was true for the dataset size it assumed. It does not survive a 19× larger one,
and the earlier claim is superseded rather than quietly dropped.

**Limits of the projection.** Fitted on 4 units of 52. Marginal novelty was
still 92% at the fourth unit, so saturation is far off, but β could move with
more units. Only one of six sampled pairs shared alleles; it overlapped 5.6%,
inside the genotype-disjoint range of 2.9–6.2%, which weakens the "my sample was
unusually novel" worry without settling it.

---

## D023 — Provenance must not depend on the downloader surviving

**Resolved:** 2026-10-06 · **Status:** RESOLVED, and the fix is PERMANENT in effect
**Evidence:** `data/raw/S3/provenance.jsonl`; `scripts/reconcile_provenance.py`

**What happened.** Four containers were fetched, three in parallel. One finished
transferring but its writer did not survive to log it, leaving a file on disk
that nothing in the provenance record accounted for. The file was **77.4%
complete** — a truncated transfer.

**Why it mattered more than a missing log line.** An unrecorded file is also an
unverified file. Had it been extracted, it would have contributed a silently
incomplete peptide table to the analysis with nothing flagging it.

**Diagnosis, not assumption.** I first suspected a concurrent-append race and
tested it: 30 simultaneous appends all landed, and the shell loop pattern was
clean. The append was never the problem. The failure is that the record is
written *after* the transfer by the same process, so anything that kills the
process between the two loses the record while leaving the bytes.

**Fix.** `scripts/reconcile_provenance.py` recovers the state from disk rather
than trusting the writer: it hashes every file lacking a record, verifies
against the publisher's checksum from the manifest, and writes the missing
entry with `reconciled: true`. It reports both directions, distinguishing a
streamed-and-deleted container from a loss by the recorded outcome. Run on S3 it
immediately identified the truncated file as `CHECKSUM_MISMATCH`.

**Second guard.** `scripts/extract_peptides.py` now **refuses** to extract a
container whose record does not show a verified publisher checksum.

**The near-miss worth recording.** SQLite happened to reject the truncated file
as malformed. That was luck: a truncation landing on a page boundary could open
cleanly and under-report rows. The checksum is the integrity check; a reader's
willingness to open a file is not one, and nothing should be built on it.

---

## D009 — Preregistration freeze mechanism · RESOLVED

**Resolved:** 2026-10-06 · **Status:** RESOLVED

**Decision: the freeze commit itself is the anchor, with `PREREGISTRATION.md`
committed at it carrying the SHA-256 of every frozen artifact.**

*Amended 2026-10-06:* this originally specified an annotated tag pushed to the
remote. The tag could not be pushed — the session credential is scoped to
`refs/heads` and the remote refused `refs/tags` — and rather than leave the
mechanism depending on an unperformed step, the commit is named as the anchor.
The change costs nothing evidentially: a tag and a commit are both created by
the repository owner with the owner's clock, so the tag was a clearer marker
rather than stronger proof. A tag may be added later without affecting the
record.

**What it does.** Names one commit as the preregistration boundary, records the
checksums of the dataset and the decision log inside the tag message rather than
only referencing them, and places the whole thing on a remote that records when
it arrived. Anyone can verify afterwards that the artifacts they are given are
the ones the preregistration covered.

**What it does not do, stated plainly because the alternative is implying
otherwise.** A git tag is created by the repository owner and its timestamp is
taken from the owner's clock. History can be rewritten and tags can be moved or
deleted. This mechanism proves **content integrity** — the artifacts match the
record — and it proves **ordering within the repository**. It does **not**
provide independent third-party evidence that the preregistration preceded
seeing any result. A reader who does not trust the repository owner gets
integrity, not chronology.

**Why that is accepted here.** Genuine independent timestamping means sending a
hash to an external service, which is a disclosure decision the author should
make deliberately rather than have made for them. The honest position is to
implement the mechanism that costs nothing, state its limit, and leave the
stronger option available: publishing only the SHA-256 of the preregistration to
an external timestamping service discloses no data and would close the gap.

**Rejected: a bare commit hash in prose**, as the decision originally proposed.
A hash written into a document proves nothing on its own — the document
containing it is as mutable as everything else. The tag at least makes the claim
a distinct, verifiable object.

---

## D010 — Seed convention · RESOLVED

**Resolved:** 2026-10-06 · **Status:** PERMANENT

**Decision: base seed 20261006 is kept. Per-purpose seeds are derived
deterministically by `scripts/seeds.py`. Seed shopping is prohibited.**

**The base is the date the preregistration was drafted.** That makes it
arbitrary in the way a seed should be — fixed in advance, with no relationship
to any outcome. Recording the convention is what matters; a seed that looks
meaningful is no better than one that looks random, provided it was chosen
before results existed.

**Per-purpose derivation, not one shared seed.** `seed(purpose)` is
`SHA-256(base:purpose:replicate)` truncated to 32 bits. One seed used everywhere
is reproducible but couples unrelated draws: the per-unit subsample and the
split would share a stream, so changing one silently reshuffles the other, and
any accidental alignment between them would be undetectable. Derivation keeps
every draw reproducible and independent.

**The substantive clause: seed shopping is prohibited.** A sensitivity analysis
over seeds uses `seed(purpose, replicate=n)` and **reports every replicate**.
Selecting the best-performing seed, or quietly re-running until a result
improves, invalidates the endpoint as surely as changing the threshold would. A
seed convention that does not forbid this is decoration.

**Runs already completed used the base seed directly** — run-001 through
run-010. That is recorded rather than retrofitted: those are exploratory and
design analyses, none of them touches the held-out partition, and rewriting
their seeds would change published numbers for no benefit. The derivation
applies from the split onward, which is where it matters.

**PERMANENT** because it governs every future stochastic step, not one choice.

---

## D006 — Predictor training-set overlap · RESOLVED

**Resolved:** 2026-10-06 · **Status:** RESOLVED as a protocol · **Gates:** G11,
and the D014 revisit

**What is being closed.** D006 asked for a handling rule, not a measurement. The
measurement cannot be made yet: it depends on which predictors enter §18, which
is not itself fixed, and on training lists not yet retrieved. What is fixed here
is the protocol, so the handling cannot be chosen after the overlap is known.

### Admission

**No predictor enters the §18 comparison until its training peptide list has
been retrieved and registered as an S6 source**, with checksum and version, like
any other input. A predictor whose outputs are available but whose training data
is not is not thereby admitted — it is admitted under the `UNVERIFIABLE` rule
below, and labelled.

### Overlap is measured at sequence level, not dataset level

Exact normalized sequence match against the frozen test partition (M7). **Dataset
provenance is not a substitute.** This submission was published 2021-09, so a
predictor released earlier cannot contain *this deposit* — but the same peptides
are observed across independent studies, and run-006 measured 20.1% of this
universe recurring across units within one study alone. Absence of the accession
from a training corpus says nothing about absence of the peptides.

### Handling, fixed per outcome

| Outcome | Handling |
|---|---|
| `CLEAN` — zero overlap | Compare on the full test partition |
| `OVERLAPPING` — overlap quantified | Primary comparison on the non-overlapping subset; full-set comparison reported as secondary with the overlap count stated |
| `UNVERIFIABLE` — training list unobtainable | Predictor is reported but **labelled**, and excluded from any claim about relative performance |

### The bias has a direction, and that makes one reading survive

Training overlap **flatters the predictor**: it scores peptides it was fit on.
So the contamination always moves the comparison against the CNN.

That asymmetry is usable. **If the CNN beats an `UNVERIFIABLE` predictor, the
result is conservative** — contamination could only have made the predictor look
better than it is, so the CNN's advantage is a lower bound. **If the CNN loses
to one, the comparison is uninterpretable**, because the gap and the
contamination are confounded and cannot be separated.

This is the only circumstance in which an unverifiable comparison may be
reported as evidence, and only in that one direction.

### Bearing on D014

D014 kept §25 primary because §18 rests on this unverifiable dependency, and
made promotion conditional on D006 resolving. The condition is now explicit:
**§18 may be promoted to primary only if every admitted predictor is `CLEAN` or
quantified `OVERLAPPING`. A single `UNVERIFIABLE` predictor blocks promotion**,
regardless of how favourable the results look — which is the point, since a rule
that bends when the numbers are good is not a rule.

### What was verified here, and what was not

Reachability only: Zenodo, IEDB and the DTU service host respond from this
environment; github.com is blocked by the network policy, so training data
distributed only through it would need another route. **Nothing about any
specific predictor's training contents has been checked**, and this entry
asserts nothing about them. Establishing that is G11's work under the protocol
above.

### Executed, 2026-10-07 — G11 PASSED (`results/qc/QC_G11.md`, D033)

**The protocol held up; two of this entry's factual premises did not.**

*Premise that failed, 1:* "github.com is blocked by the network policy." That
was measured on the bare domain, which returns 400. **Release asset URLs return
200 and transfer normally**, and every MHCflurry artifact is a release asset, so
the training data was obtainable all along.

*Premise that failed, 2:* S6 recorded predictor training sets as "not reliably
obtainable". **Each MHCflurry model bundle ships its own per-component
`train_data.csv.bz2`**, so the exact training footprint of the released
predictor is available, not an approximation of it. `UNVERIFIABLE` went unused.

**Both predictors admitted as quantified `OVERLAPPING`:** MHCflurry 2.0.0 at
8.29% of test positives and 1.20% of negatives; 2.3.0 at 9.11% and 1.16%.

**This entry's two substantive claims were both confirmed by measurement.**

The direction argument: the overlap is **6.9:1 and 7.9:1 biased toward
positives**, so contamination hands the predictor peptides it was fit on and
almost none of the decoys it must reject. Measured, not assumed.

The rejection of provenance-as-substitute: the 2.0.0 models predate this
deposit's 2021-09 publication by fifteen months and name it nowhere, and
**8.29% of this test partition's positives are in their training data anyway**,
reaching it through other studies. Had date been accepted, that line would have
been called `CLEAN` and the comparison would have carried an 8% contamination
nobody had counted. This is the entry's most load-bearing paragraph and it was
right.

**Result.** On rows naive to both systems, the CNN beats MHCflurry 2.0.0 by
+0.1378 (CI99 [+0.1151, +0.1583]) and 2.3.0 by +0.1340 (CI99 [+0.1126,
+0.1505]), 10 of 10 participants each. The advantage is **largest** where
contamination is smallest, so it is not produced by memorisation.

**Not promoted.** This entry's condition for promotion — every admitted
predictor `CLEAN` or quantified `OVERLAPPING` — is now met, and D014's bar on
post-hoc switching is unchanged. §25 was read and closed before any predictor
score existed. §18 stays secondary.

**The comparison is not a fair test of predictor quality, and QC_G11 §4 says so
with numbers**: 11.78% of set-C negatives are ranked strong presenters by
MHCflurry, so the task differs from the predictor's, and the CNN additionally
trained on this cohort's own instruments and negative construction.

---

## D026 — Architecture, representation and training protocol frozen · RESOLVED

**Resolved:** 2026-10-06 · **Status:** PERMANENT until superseded

**Why this exists.** Writing the Methods section exposed that §§11–13 were never
frozen, and had been carried silently past the preregistration commit. The
dataset, split, endpoint and decision rule were fixed; the model was not. That
left latitude in exactly the component whose behaviour the experiment measures —
a frozen dataset is no protection if the network can be adjusted until the
number comes out right.

**What is now fixed.** Topology (two convolutional blocks, global max-pool,
dense, sigmoid), the encoding, and every training parameter including a
16-point grid and the selection rule. Detail in `SECTIONS.md` §§11–13.

**Three choices worth defending rather than asserting.**

*Two convolutional blocks, not more.* After two kernel-3 blocks with one pooling
step the receptive field already spans all 12 positions. Further depth cannot
see more of the peptide; it only adds capacity, which works against the stated
purpose of testing whether a minimal model finds local sequence signal.

*Centre-padding, not right-padding.* This is the one place domain knowledge
enters the encoding, and it is declared. Right-padding would place the
C-terminal residue at a different index for each of the five lengths, forcing
the network to learn five separate C-terminal motifs from a representation that
obscures their alignment. Centre-padding removes an artefact; it does not tell
the model which residues matter.

*Length is not a feature.* The padding makes it recoverable, and supplying it
explicitly would let the model exploit length imbalance — which does not exist,
since the negatives are length-matched exactly, so the feature could only
contribute noise or a route to overfitting.

**Reduction order fixed here**, as D022 required, so it cannot be chosen once a
budget is already under pressure: configurations halve by dropping `E = 16`
first, then `p = 0.0`.

**Compute verified against the gate**: 105 runs, 24.7 h at the 100-epoch worst
case against a 96 h cap.

**Consequence.** The preregistration is now complete. Any deviation from §§11–13
requires a new decision entry and renders the affected claim exploratory.

---

## D027 — How 25 final models yield one endpoint · RESOLVED

**Opened and resolved:** 2026-10-06, **before the held-out partition was read**
**Evidence:** `results/model/cv_results.json`; §13; D010

**The gap.** §13 fixes the final fit at five folds × five seeds and requires all
25 be reported, but never states how 25 models produce the single number the
decision rule is applied to. Found while implementing the evaluation, with the
test partition still unread, so it can be closed without any result influencing
it.

**Decision.** For each held-out unit, average precision is computed separately
under each of the 25 models and **averaged across models**; the estimand is the
mean of those per-unit values, and the cluster bootstrap resamples units. The
25 individual per-unit matrices are reported.

**Why not ensemble the scores.** Averaging the 25 models' outputs and scoring
once would measure an ensemble of 25 networks. §25 asks whether *a* CNN trained
on these data carries signal, and an ensemble is reliably better than its
members, so that framing would answer a more flattering question than the one
preregistered. Score-ensembling is reported as a **secondary** figure, labelled
as such.

**Why average APs rather than take the best or the median of 25.** Taking the
best is seed selection, prohibited by D010. The median discards information for
no gain at this spread. Averaging gives the expected performance of one model
drawn from the preregistered procedure, which is what the hypothesis is about.

**Bootstrap unit is unchanged.** Units, not models and not peptides — the
quantity bounding every claim is the number of independent participants
(run-001).

---

## D008 — §25 decision rule · RESOLVED

**Resolved:** 2026-10-06 · **Evidence:** run-012 (`results/power/decision_rule.json`),
run-001 F3, D002

**Decision: reject the null if the lower bound of a nominal-99% cluster-bootstrap
interval on the mean per-unit average precision exceeds 0.647.**

That is the measured composition floor of 0.597 (D002) plus a lift of 0.05.

### Two separate things had to be fixed, and only one was a choice

**The interval had to be made honest first.** run-001 F3 found nominal 95%
intervals under-covering; measured at the frozen conditions — 10 test units,
1:1 — they deliver **0.884–0.890** actual coverage. A rule stated at 95% would be
stricter in name than in fact.

| nominal | actual coverage (τ = 0.10 / 0.25 / 0.50) |
|---|---|
| 95% | 0.890 / 0.890 / 0.884 |
| 97.5% | 0.926 / 0.928 / 0.918 |
| **99%** | **0.962 / 0.954 / 0.944** |

**Nominal 99% is adopted**, delivering ~95% actual. This applies to every
interval reported from this design, not only the decision rule — reporting a
nominal 95% interval anywhere would overstate precision by the same margin.

**Then the threshold, which is a judgement.** Power at the adopted interval:

| true AUROC | true AP | lift over floor | power at floor+0.05 | power at floor+0.10 |
|---|---|---|---|---|
| 0.70 | 0.6875 | +0.091 | **0.42** | 0.01 |
| 0.75 | 0.7390 | +0.142 | **0.98** | 0.49 |
| 0.80 | 0.7913 | +0.194 | 1.00 | 0.99 |

False positive rate with the true value *at* the floor: 0.020 at a +0.00
threshold, **0.000** at +0.05.

**floor+0.05 is adopted.** floor+0.10 is underpowered — 0.49 at AUROC 0.75 means
a real and substantial effect would be missed half the time, which is a worse
failure than the marginal strictness it buys.

### The limitation this rule carries, stated rather than buried

**Power is 0.42 at AUROC 0.70.** A genuine but modest effect — a lift of 0.09
over the floor — will be missed more often than not. The minimum reliably
detectable effect is a lift of roughly **0.14 AP**, equivalent to AUROC ≈ 0.75.

This follows from 10 held-out units, which is fixed by the data and not by any
choice made here. Failure to reject is therefore **not** evidence of no signal;
it is consistent with a real effect below the detectable range, and §20's
interpretation must say so rather than reporting a null as an absence.

### How far this has moved from the proposal

§25 asked for "better than chance". run-001 F1 showed that passes at AUROC 0.60
with power 1.00 — nearly unfalsifiable. The rule now tests against a measured
composition floor rather than chance, on an interval calibrated to its actual
coverage rather than its nominal label, at a threshold chosen for power rather
than convenience. The hypothesis is finally capable of failing.

---

## D003 — Cross-split sequence leakage · RESOLVED

**Resolved:** 2026-10-06 · **Evidence:** run-010 (`results/qc/QC_G5.md`), run-006

**Decision: shared sequences are kept. The primary metric is computed on the
full test partition; the leakage-free subset is reported alongside as a
preregistered sensitivity analysis.**

**The measurement that forced this.** Over 2,000 random 10-unit test
partitions, **14.59%** of test positives also appear in training (range
11.76–17.25%). That is higher than the 10.20% row-level duplication, because a
test unit's sequences get 42 independent chances to appear among the training
units — exposure compounds with the number of training units rather than
staying at the pairwise rate.

**Unit-disjointness is not sequence-disjointness.** The proposal's §9 lists them
as separate leakage types but the design treats satisfying the first as
delivering the second. It does not: roughly one test positive in seven has been
seen verbatim during training.

**Why keep them rather than drop them.** Dropping shared sequences from the test
set would make it unrepresentative in a specific direction: the unit-private
80% of the universe is enriched for peptides seen once, which are plausibly the
noisiest and least reproducibly presented. A test set purged of everything
shared would measure performance on exactly the subset least likely to be real.
That trades a known, bounded bias for an unknown, unbounded one.

**Reporting both is what makes it honest.** The gap between the full-test and
leakage-free metrics *is* the inflation, measured rather than argued. A claim
that survives both is sound; a claim that only survives the full set is a claim
about memorisation.

**Rejected: dropping from training instead.** It discards real observations and
still leaves the test set's composition altered relative to the universe.

---

## D034 — Final freeze · RESOLVED

**Resolved:** 2026-10-07 · **Record:** `FREEZE_RECORD.md`, `freeze_manifest.json`
**Mechanism:** `scripts/freeze.py` · **Follows:** D009, which froze the
preregistration by the same method

**Decision: the repository is frozen by a manifest that cannot be written
unless the tree verifies first.**

### Why verification comes before checksums

D009 froze the preregistration with a checksum list, and that was the right
instrument for what it had to prove: that six named artifacts matched a record.
A final freeze covers 348 files and a set of conclusions, and a checksum list
over an unverified tree would prove only that a mess was reproducible.

So `--write` runs `--verify` first and refuses on any failure. Eight checks:

| # | Check | Result |
|---|---|---|
| 1 | Working tree clean, nothing untracked | pass |
| 2 | Preregistration checksums still hold — dataset and split unmoved since `f7550f54` | 6 artifacts |
| 3 | Every artifact, script and figure `REPORT.md` names resolves | pass |
| 4 | Every headline number in `REPORT.md` appears verbatim in its artifact | 25 numbers |
| 5 | Figures regenerate byte-identically from the artifacts | 7 figures |
| 6 | Every QC gate passed or carries a recorded unavailability | G1–G13, FINAL |
| 7 | Every decision resolved, none left OPEN | D001–D033 |
| 8 | An existing manifest still agrees with the tree and declares its own exclusion | 349 entries |
| 9 | The trainer's selftest passes | pass |

**Check 2 is the one that matters most.** It proves the frozen dataset and split
are byte-identical to what the preregistration committed to, so every result in
this repository was computed on the data the endpoint rule was written against.
Without it, "preregistered" is a claim about intent; with it, it is a claim about
bytes.

**Check 5 was added because the figures are derived twice over** — from
artifacts that are themselves derived from the dataset. A figure that cannot be
regenerated is a figure whose relationship to the data is unverifiable, and
regenerating them is cheap.

**The verifier found two defects, both in itself or in the freeze rather than in
the work.** Check 7 initially read only entry headings and reported six resolved
decisions as open, because D001, D014, D015, D020, D022 and D023 carry their
status in the body — the log was right and the check was wrong. Then the first
manifest listed **itself** with a stale hash, because hashing a file and then
overwriting it stores the previous version's digest; the verification command
printed in `FREEZE_RECORD.md` caught it on the next run. The manifest now
excludes itself and declares the exclusion, and check 8 was added so the failure
is caught before a commit rather than after one.

Both are recorded because a verification tool that has never produced a failure
has not been tested, and this one's first two failures were its own.

### The anchor

**The anchor is the commit that adds `freeze_manifest.json`.** A manifest cannot
contain the hash of the commit that carries it, so the manifest records its
parent and `FREEZE_RECORD.md` states the pair: the anchor is the single child of
that parent which introduces the manifest.

**One superseded anchor.** `cc0a6217` carried the self-inconsistent manifest and
is left in history rather than rewritten, since the branch was already pushed.
The live anchor is the later commit that adds the corrected manifest.

**No tag, again.** One was attempted and the remote refused it, exactly as it
refused the preregistration tag (D009) — the session credential is scoped to
`refs/heads`. Recorded rather than worked around, and the second occurrence
confirms it is the environment rather than a one-off.

### What this freeze does not assert

**Not that the conclusions are right.** It asserts the tree is internally
consistent and that the prose's numbers are the artifacts' numbers. A checksum
can carry the second claim and not the first.

**Not independent chronology.** As D009 said of the preregistration: created by
the repository owner, with the owner's clock. It fixes ordering within the
repository and nothing outside it.

**Not completeness.** Three things are unavailable rather than done, each
recorded in `SECTIONS.md`: NetMHCpan and MixMHCpred for §18, negative-control
robustness for §20, and a second symmetric allele pair. A second cohort is the
only route to the last two.

**Not that §20 is safe.** It rests on D032, where a criterion I had written was
narrowed after it failed, with the project owner's acceptance. The freeze
preserves that fact; it does not settle it.

---

## D033 — §18 admission: both MHCflurry lines are quantified `OVERLAPPING`, and the comparison subset must be mutually naive · RESOLVED

**Opened and resolved:** 2026-10-07 · **Executes:** D006's protocol · **Gate:** G11
**Before any predictor score was computed.**

### Three things D006 assumed that turned out to be wrong, all in the helpful direction

**1. GitHub is reachable for release assets.** D006 recorded "github.com is
blocked by the network policy, so training data distributed only through it
would need another route." That was inferred from the bare domain returning
400. **Release asset URLs return 200 and transfer normally** — a 160 MB model
bundle downloaded without incident. Every MHCflurry artifact is a GitHub release
asset, so all of them were obtainable all along. D006's pessimism about
obtainability was a measurement of the wrong URL.

**2. The training list is shipped with the model.** D006 expected to compare
against a predictor's published training corpus, and S6 recorded training sets
as "not reliably obtainable". **Each MHCflurry model bundle ships its own
`train_data.csv.bz2` per component** — affinity predictor, processing predictor
with and without flanks. The union of those is the exact training footprint of
the released predictor, not an approximation of it.

This matters specifically for the 2.3.0 line. Release 2.3.0's manifest pairs
**2026-09-28 models with a 2023-10-23 curated file**, so checking against the
declared curated release would have bounded the overlap below and left the line
effectively `UNVERIFIABLE`. Against the bundle's own training data it is exactly
measurable.

**3. Both lines are admissible.** D006's admission rule is satisfied for both:
training lists retrieved, registered as S6 sources with sha256 and version,
overlap measured at sequence level by exact match (D016 — nothing fuzzy).

### M7 outcomes

| | MHCflurry 2.0.0 | MHCflurry 2.3.0 |
|---|---|---|
| models | `models_class1_presentation.20200611` | `models_class1_presentation.20260928` |
| training peptides (union over components) | 605,189 | 666,025 |
| overlap with test **positives** | 8,093 — **8.29%** | 8,893 — **9.11%** |
| overlap with test **negatives** | 1,199 — **1.20%** | 1,157 — **1.16%** |
| per-unit positive overlap | 4.89–15.42% | 5.22–17.88% |
| **M7 verdict** | **`OVERLAPPING`, quantified** | **`OVERLAPPING`, quantified** |

**D006's reasoning about direction is confirmed by measurement.** The overlap is
**6.9:1 and 7.9:1** biased toward positives over negatives. Contamination gives
the predictor peptides it was fit on, and almost none of the decoys it must
reject, so it moves the comparison against the CNN by construction.

**D006's rejection of provenance-as-substitute is also confirmed.** Neither
line's training sources name PXD024871, and the 2.0.0 models predate this
deposit's 2021-09 publication by fifteen months — yet **8.29% of this test
partition's positives are still in its training data**, reaching it through
other studies. Had date been accepted as evidence, the 2.0.0 line would have
been called `CLEAN` and the comparison would have carried an 8% contamination
nobody had counted.

### The refinement: the primary subset must be naive to BOTH systems

D006's handling for `OVERLAPPING` is "primary comparison on the non-overlapping
subset". Taken literally that means removing the **predictor's** overlap.

**That would hand the CNN a selectively easier dataset, which §18 forbids in
those words.** D003 measured 15.99% of test positives as also present in the
CNN's training data. Removing only the predictor's 8–9% while leaving the CNN's
16% in place would strip one system's memorisation advantage and preserve the
other's — and the resulting number would favour the CNN for a reason that has
nothing to do with either model's quality.

**Decision: the primary §18 row set excludes any test sequence that appears in
the training data of *either* system.** Reported alongside it, so the effect of
each correction is visible rather than argued:

| Row set | What it shows |
|---|---|
| **mutually naive** (primary) | neither system has seen any sequence scored |
| predictor-naive only (D006 as literally written) | what removing only the predictor's overlap does |
| full test partition (D006's secondary) | both memorisation advantages left in, overlap counts stated |

This is the same rule the allele analysis already runs under: D030's standing
check requires every evaluation subset to report what each compared model had
already seen, and a subset defined so that one side has seen it and the other
has not is void. Applying a weaker rule to §18 than to §20 would be
inconsistent.

### What this does not change

**§18 is not promoted.** D014 made promotion conditional on every admitted
predictor being `CLEAN` or quantified `OVERLAPPING`, which is now true — so the
condition is met. **D014 equally says a switch after seeing results is endpoint
switching regardless.** §25 was read, closed and reported before any predictor
score existed. §18 stays secondary, and that this entry *could* have argued for
promotion is the reason to say plainly that it does not.

**`UNVERIFIABLE` goes unused, so D006's one-direction rule is not invoked.** No
predictor here is reported under it, and the asymmetry argument that made it
usable is not needed.

### Predictors not obtained, with reasons

| Predictor | Status |
|---|---|
| NetMHCpan 4.1 | **not obtained** — distribution is behind a per-user academic licence form at the DTU host; not scriptable, and accepting a licence on the owner's behalf is not mine to do |
| MixMHCpred | **not obtained** — distributed via `raw.githubusercontent.com`, which returns 404 through this proxy, unlike release assets |

Both are absent from §18 and neither is reported. §18's input list named
"NetMHCpan, MixMHCpred, or others"; the comparison runs on MHCflurry alone and
says so.

**Seeds.** `seed('predictor_bootstrap')` for intervals. No training is done
here — the CNN models are the frozen final 25 (D027) and the predictors are
released artifacts.

### Outcome, 2026-10-07

**The refinement mattered, and less than expected.** The primary mutually-naive
contrast is **+0.1378 / +0.1340**; D006's literal predictor-naive-only version
gives **+0.1393 / +0.1347** — within 0.002. Stripping the CNN's leakage as well
barely moves the gap, so the stricter subset was the right call on principle and
changed no conclusion.

**What did move is the full-partition comparison: +0.0922 / +0.0877.** MHCflurry
gains more from its own overlap (0.5481 → 0.6629) than the CNN does from its
(0.6859 → 0.7551), so leaving both advantages in *narrows* the gap. The
contamination was working against the CNN, exactly as D006 said it would.

**A caveat on reading those three numbers side by side.** Average precision
depends on prevalence, and the subsetting moves it from 0.440 to 0.500. Within
each row set the systems are on identical rows and the paired contrast is exact;
across row sets the absolute values are not comparable.

**An incidental finding, recorded because nothing else would have caught it.**
MHCflurry refused a peptide containing `X`, which surfaced that the frozen
positives hold **181 rows (0.035%) with ambiguity codes** — X, B (Asx), Z (Glx)
— and that the CNN's encoder maps an unknown character to the **pad token**. Those
peptides were therefore encoded with internal pads rather than rejected or
flagged. 22 are in the test partition, 0.011% of its rows, so the endpoint is
unaffected at any decimal place that matters. The defect is in the encoder's
silent `IDX.get(ch, 0)` fallback and in a selftest that checks only standard
residues, and it is the same shape as the bug that once deleted the middle of
every long peptide: an encoder accepting input it should have rejected.

---

## D032 — G13: narrowing the release criterion · ACCEPTED

**Opened:** 2026-10-07, after `QC_G12_multi_allele.md`
**Status: ACCEPTED by the project owner, 2026-10-07** — "accept the narrowing".
**G13 RELEASED. §20 written to the wording below, unchanged.**
**Depends on:** D031 (the criterion), D029, D030

**This entry proposes relaxing a criterion I wrote and am now failing. That is
self-serving by construction, which is why it is a proposal rather than a
decision, and why the case against it is stated as fully as the case for.**

### The situation

D031 set four conditions for releasing G13. Three are met:

| Condition | Result |
|---|---|
| Sign reversal in Part B | met — +0.0476 on A\*02:01-exclusive, −0.0049 on C\*07:02-exclusive |
| Both neutral estimates near zero | met — −0.0013 and −0.0038 |
| Part A's five contrasts consistent | met — all five positive, three of five excluding zero |
| **Both Part B directions' intervals excluding zero** | **fails** — the C\*07:02 side does not |

### The case for narrowing it

**The failing condition was close to unattainable when it was written.** D031
fixed Part B's carrier tests at 9 and 6 units and printed those numbers, then
required a nominal-99% paired interval from the 6-unit side to exclude zero. The
C\*07:02-exclusive stratum turned out to hold 542 sequences and 1,878 rows, the
smallest in the run. Requiring significance from that arm was a condition the
design could not supply, and I should have seen it from my own table.

**It is the same error twice.** D029's defect was a symmetry assumption its own
groups could not satisfy. D031's is a power requirement its own unit counts
could not satisfy. Both are reading rules written without checking that the
design can produce the evidence the rule demands.

**What the data do show is strong where the design has power.** On the A\*02:01
side: +0.0476, CI99 [+0.0314, +0.0626], 9 of 9 units, with memorisation,
recurrence and training-set quality each measured at zero on the same units, on
a design where both arms are carrier-trained so neither group is defined by an
absence. Part A reproduces the direction in all five alleles, and catches a false
positive (A\*01:01, raw +0.0229, adjusted +0.0083) that only the neutral estimate
could have caught.

**The proposed criterion, which is what I should have written:** sign reversal
in Part B, **one** direction's interval excluding zero, both neutral estimates
near zero, and Part A's contrasts consistent in direction. That is met.

### The case against narrowing it

**A criterion relaxed after it fails is not a criterion.** The whole value of
D008, D025, D029 and D031 is that the reading was fixed before the numbers. If
the rule bends when the numbers arrive, nothing in this project's preregistration
means anything, and the reader has no way to tell a principled narrowing from a
convenient one.

**The one-direction version is weaker than it looks.** A sign reversal where only
one arm reaches significance is also what you would see if the A\*02:01 arm's
training set happened to suit A\*02:01-exclusive peptides for a reason unrelated
to the allele. The neutral estimate argues against that, but on 9 units.

**The C\*07:02 failure may not be power.** `QC_G12_multi_allele.md` §2.2 offers
a biological reading — lower HLA-C surface expression, so more contamination in
a C-exclusive stratum — but that is a post-hoc hypothesis about the same
allele's peptides, not independent evidence. A real absence of allele-specific
signal at the C locus would look exactly the same.

**Nothing downstream is blocked.** §25 is read and closed. §20 being unwritten
costs the project nothing but a section.

### What release would and would not license

If the owner accepts, §20 may state **only** this:

> The model learns sequence features linked to donor genotype. For HLA-A\*02:01
> this is demonstrated allele-specifically: a model trained on carriers ranks
> peptides exclusive to carriers above a model trained on carriers of a
> different allele, on held-out participants, by 0.048 average precision
> (nominal-99% CI 0.031–0.063, 9 of 9 units), with memorisation, peptide
> recurrence and training-set quality each measured at zero on the same units.
> The direction reproduces across five alleles. It is not demonstrated for
> HLA-C\*07:02. The effect is a few hundredths of average precision on strata
> comprising 0.5–5% of each ligandome.

And §20 may **not** state: that the primary endpoint's lift is presentation
biology; that the restricting allele is identified (no deconvolution was done,
and linkage is uncontrolled); that anything generalizes beyond this cohort,
disease, tissue and laboratory; or anything about HLA-C.

**If the owner refuses**, G13 stays held, §20 stays unwritten, and the results
remain where they are — in `QC_G12_multi_allele.md` and R12, which state them
in full either way. **Refusing costs no evidence.**

### The third option

Run more alleles. The cohort has A\*24:02 (16 carriers), B\*07:02 (15) and
C\*03:04 (14). None pairs with another at both-sides-≥14 — the pair table in
D031 shows the candidates leave 1–4 units on the minority side — so no second
symmetric Part B is available in this dataset. **The symmetric test cannot be
replicated here.** A second cohort would be required, which is outside this
project's scope.

**Recommendation.** Accept the narrowed criterion, because the condition that
failed was unattainable by construction and the surviving evidence is strong in
the direction the design can measure — but only with the §20 wording above,
which is narrower than the criterion change might seem to permit. I hold the
recommendation lightly: refusing is defensible and costs nothing but a section.

### Resolution

**The project owner accepted the narrowing on 2026-10-07.** The operative
criterion for G13 is therefore: *sign reversal in Part B, **one** direction's
interval excluding zero, both neutral estimates near zero, and Part A's
contrasts consistent in direction.* Met.

**What was done on acceptance.** §20 was written using the wording in this
entry **verbatim**, and the "may not state" list above was carried into it as an
explicit block, so the narrowing cannot widen by paraphrase later. The case
against narrowing stays in this entry unaltered; it is the record of what the
acceptance overrode.

**Two §20 items were not satisfied by the acceptance and are recorded as
deferrals, not bypassed** (the gate schedule forbids silent reduction):

1. **Robustness across peptide lengths — now DONE**, and it was not before.
   `scripts/endpoint_by_length.py` decomposes the already-read endpoint by
   length over the same 200,000 rows and the same 25 models. The pooled value
   reproduces at 0.7551 exactly. All five lengths clear the D008 threshold:
   8-mer 0.7649, 9-mer 0.7660, 10-mer 0.7297, 11-mer 0.7421, 12-mer 0.7850,
   spread 0.0553. Not a second reading — every length is reported, none is
   selected, and the primary decision is fixed and unchanged.
2. **Robustness across negative-control designs — STRUCTURALLY UNAVAILABLE.**
   §20's methodology asks for it, but D002 selected set C and the dataset was
   frozen with set C alone: `NEGATIVES.csv` holds 520,000 set-C rows and no
   alternative. Evaluating sets A or B would mean rebuilding a frozen dataset,
   which the freeze forbids. The composition diagnostic that chose set C
   (`negative_diagnostic.json`: A 0.6120, B 0.5000, C 0.6085) is the only
   evidence on this axis and it is a property of the data, not of the model.
   Recorded as a permanent limitation of the frozen design rather than as work
   outstanding.

---

## D031 — Multi-allele test: replication across five alleles, plus one symmetric pair · RESOLVED

**Opened and resolved:** 2026-10-07 · **Before any multi-allele result was visible**
**Requested by the user** after `QC_G12_allele.md` §4 named this as the test that
would settle D029 · **Depends on:** D029, D030 · **May release:** G13

**Decision: run the per-allele design across the five most frequent class-I
alleles, and add the one allele pair whose groups both share an allele. The
second is the decisive test; the first is replication.**

### Why the D029 design cannot be fixed by repeating it

D029's contrast II failed as a confirmation test because the two groups are not
symmetric: carriers of HLA-A\*02:01 share that allele, while non-carriers share
only its absence. **That defect is not specific to A\*02:01 — it holds for every
allele split.** "Non-carriers of A" is never a group with a shared motif, so no
single-allele design can produce a symmetric replication. Repeating D029 for
more alleles multiplies the evidence but never removes the asymmetry.

So the test has two parts, and only the second is symmetric.

### Part A — replication across five alleles

For each allele below: train one arm on carriers, one on non-carriers, 8
training units and 2 early-stopping units each (equal, platform-stratified per
D025), and score both on the held-out carriers' **A-exclusive stratum**.

| Allele | carriers | certain non-carriers | carrier test units |
|---|---|---|---|
| HLA-A\*02:01 | 29 | 21 | 19 |
| HLA-C\*07:02 | 24 | 23 | 14 |
| HLA-A\*01:01 | 17 | 29 | 7 |
| HLA-A\*24:02 | 16 | 30 | 6 |
| HLA-B\*07:02 | 15 | 31 | 5 |

Five splits with five different group compositions. The "this particular
training set was simply better" account would have to hold five times, each time
favouring the carrier side, and the neutral estimate measures it directly in
each.

### Part B — the symmetric pair, which is the decisive test

**HLA-A\*02:01 and HLA-C\*07:02 are the only pair whose mutually exclusive
groups are both large enough.** **Corrected before the run:** the 20 / 15 figures
first written here were computed by absence alone, ignoring the locus-certainty
rule this same entry mandates two sections below — an internal inconsistency in
this entry, found when the code applied the rule. Requiring the *excluded*
allele's locus to be fully typed gives **17** units carrying A\*02:01 and
certainly not C\*07:02, and **14** carrying C\*07:02 and certainly not
A\*02:01. Six units train and 2 validate on each side, leaving carrier tests of
**9 and 6**. The smaller figures are what the run uses.

Both arms are carrier-trained — each for its own allele — so **there is no
asymmetry**. Each is scored on both exclusive strata:

| | A\*02:01-exclusive stratum | C\*07:02-exclusive stratum |
|---|---|---|
| expected if allele-specific | M_A02 **>** M_C07 | M_C07 **>** M_A02 |
| expected if one training set is better | same sign on both | same sign on both |

**A sign reversal between the two strata is the signature of an allele effect,
and it is what D029's contrast II could not deliver.** Fixed here before the
numbers exist. The other eight candidate pairs leave 1–4 test units on the
minority side and are not run; the sizes are in this entry so the choice is not
a selection made later.

### Non-carriage must be locus-certain, and was not

**New finding, recorded here.** D012 noted 14 of 52 units have PARTIAL typing
and none imputed. What PARTIAL means at locus level was not: each of those 14
units reports **one** allele at one or two loci instead of two, which is
homozygosity and untyped-second-allele being indistinguishable in the SDRF. So a
unit reporting one HLA-A allele that is not A\*02:01 may still carry A\*02:01 at
the untyped position.

A unit therefore counts as a non-carrier of A here only if it reports **two**
alleles at A's locus and neither is A. Effect on the groups:

| Allele | non-carriers by absence | **uncertain** (locus under-typed) | certain |
|---|---|---|---|
| A\*02:01 | 23 | 2 — UPN10, UPN16 | 21 |
| C\*07:02 | 28 | 5 | 23 |
| A\*01:01 | 35 | 6 | 29 |
| A\*24:02 | 36 | 6 | 30 |
| B\*07:02 | 37 | 6 | 31 |

**This touches D001 and D029 retroactively:** 2 of the 23 units used there as
A\*02:01 non-carriers have an under-typed A locus, so 21 of 23 are certain. The
contamination is 8.7% and in the direction that would *weaken* an allele
effect, so it does not explain D029's +0.0335 — but it was not stated and is
now.

The **absence** requirement in each stratum definition still ranges over *all*
non-carriers including the uncertain ones, which is the conservative direction:
it can drop a genuinely restricted peptide, never admit an unrestricted one.

### Carried forward from D030

Every row set excludes positives either compared arm saw in training, and
**every evaluation reports the seen-fraction for each arm** — the standing check
D030 added after the first stratum turned out to be 97.93% memorised by one arm
and 0.00% by the other. Each comparison also carries its own composition-only
floor, its own recurrence-matched control, and its own direct estimate of the
training-set quality difference on class-shared peptides.

### How Part A is read, fixed now

Each allele's contrast is reported with its own paired cluster-bootstrap
interval, and the sign pattern across the five is reported as a count.
**No joint p-value is computed.** The five splits draw from 52 units and most
units appear in several of them, so the contrasts are correlated and a sign test
treating them as independent would overstate the evidence. Replication here
means a consistent pattern across correlated splits, which is weaker than five
independent confirmations and is reported as such.

### Limits accepted in advance

1. **Three of the five carrier tests have 7, 6 and 5 units.** Their intervals
   will be wide; they contribute signs, not magnitudes.
2. **Part B's arms train on 6 units** against Part A's 8 and D029's 12, so Part
   B's absolute numbers are not comparable to either. Only its internal sign
   reversal is.
3. **Still one cohort, one disease, one laboratory**, and still no allele
   deconvolution: "A-exclusive" means exclusive to carriers of A, which includes
   peptides restricted by alleles in linkage with A.
4. **All arms train on units inside the primary test partition**, as every
   secondary analysis since R10 has. None serves §25, which is closed.

### What would release G13

Part B showing the sign reversal, with both directions' intervals excluding
zero and both neutral estimates near zero, and Part A's five contrasts
consistent with it. Anything less leaves G13 held. Part B failing to reverse
closes the allele-specificity question negatively for this dataset, and that is
the outcome this entry is equally prepared to record.

**Seeds.** `seed('multi_split', i)` per allele for the pools,
`seed('multi_valsplit', i)` for the early-stopping units,
`seed('multi_init', i)` for weights, `seed('multi_bootstrap')` for intervals,
`seed('multi_negatives')` for the 1:1 stratum negatives. Five replicates per
arm; per-unit AP is the mean across them (D027).

### Disclosure: a plumbing run previewed Part B's direction

The plumbing test needed to validate this code — Part B, one seed, two epochs —
necessarily computed the contrasts, so **Part B's direction was visible before
the real run.** It showed +0.0308 on the A\*02:01-exclusive stratum and −0.0189
on the C\*07:02-exclusive stratum: the sign reversal this entry preregistered.

Disclosed rather than omitted. Two reasons it cannot bias the result, and one
reason it is still a cost:

- **Nothing remained to choose.** The alleles, the pair, the group definitions,
  the pool and validation draws, the three strata per allele, the seeds and the
  reading rule were all fixed in this entry and committed before the plumbing
  run. A preview can only bias an analysis that still has a free parameter.
- **A 2-epoch single-seed fit is not the model.** The real arms train to early
  stopping over five seeds, so the preview's numbers are not the result's.
- **The cost is to me, not the design.** I now know the direction, and a reader
  must take on trust that no unlogged choice followed. That is why this
  paragraph exists and why the commit history is the check: the design commit
  precedes the run.

A better sequence would have validated the plumbing on a row set that is not
one of the reported ones — scrambled group labels, for instance. That is the
practice to adopt for the next analysis of this shape.

### Outcome, 2026-10-07 (`results/qc/QC_G12_multi_allele.md`)

**Part B reversed, as preregistered.** On the A\*02:01-exclusive stratum the
A\*02:01-trained model beats the C\*07:02-trained one by **+0.0476** (CI99
[+0.0314, +0.0626], **9 of 9 units**) after adjusting for the neutral
training-set difference; on the C\*07:02-exclusive stratum the sign flips to
−0.0049. Memorisation is 0.00% on all 21 row sets, and for the A\*02:01
direction recurrence (+0.0052) and training-set quality (−0.0013) are both
measured at zero on the same units. **This is the symmetric demonstration D029
could not produce.**

**The C\*07:02 direction demonstrates nothing** — correct sign, interval
containing zero, 6 units, 542 stratum sequences.

**Part A: all five adjusted contrasts positive**, three of five excluding zero,
four of five excluding zero against the recurrence control. The neutral estimate
earned its place by catching a false positive: A\*01:01 reads +0.0229 raw, but
its neutral δ is +0.0146 (CI99 [+0.0010, +0.0270]) — the carrier arm is simply
the better model for that split — and only +0.0083 survives adjustment. Without
it, A\*01:01 would have been counted as a replication.

**Both designs rank A\*02:01 above C\*07:02** (+0.0337 / +0.0160 in Part A;
+0.0476 / −0.0049 in Part B), a coherence check the design did not have to pass.

**G13 stays held: three of this entry's four release conditions are met and the
fourth fails.** The fourth required a nominal-99% interval from a 6-unit arm,
which this entry's own table shows was close to unattainable — the same family of
error as D029's symmetry assumption. **D032 proposes the narrowing and leaves it
to the project owner**, because the criterion is mine and relaxing it to pass is
self-serving by construction.

---

## D030 — The D029 stratum was defined so that one arm had memorised it · RESOLVED

**Opened and resolved:** 2026-10-07, on inspecting the D029 run before reporting it
**Supersedes:** the stratum definition in D029 · **Does not supersede:** anything else in D029

**Decision: the stratum contrast in `allele.json` is void. Every evaluation
subset must be restricted to sequences neither arm saw in training, and the
corrected analysis in `allele_leakfree.json` is the one that is reported.**

**The flaw.** D029 defined a sequence as carrier-restricted if it was observed
in ≥2 of the 15 C_pool units and in none of the 15 N_pool units. C_pool is
M_AM's training pool; N_pool is M_AD's. The definition therefore *required* that
the sequence be present in M_AM's side of the data and absent from M_AD's.
Measured on the held-out carriers' stratum rows: **97.93% are sequences M_AM
trained on, 0.00% are sequences M_AD could have trained on.** The +0.0660 it
produced measures memorisation, and it was the largest effect in the run.

**How it got past the design.** D029 did validate the stratum — on held-out
units, finding carrier-restricted peptides reach held-out carriers at 2.08× the
per-unit rate of held-out non-carriers. That check confirmed the stratum tracks
carrier linkage. It said nothing about **what each arm had already seen**, which
is a different question, and the one that mattered.

**This is the second occurrence of one failure mode.** The first `TEST_LEAKFREE`
mask selected a subset containing no negatives, making average precision 1.0000
by arithmetic. Both times a subset was defined by a property that fixed the
answer, and both times the broken version produced the most flattering number in
the run. **Standing check, from here on: for every evaluation subset, report
what fraction of it each model being compared had already seen in training.**
A subset whose definition references a model's training units is void until
that fraction is shown to be equal across the models compared.

**The correction.** `scripts/allele_leakfree.py` rebuilds every row set
excluding positives either matched arm saw in training, so both models are
equally naive to every sequence scored. Carrier-linkage survives as recurrence
among **held-out** carriers plus absence from every non-carrier. A
recurrence-matched control — equally recurrent, equally unseen, not exclusive to
a class — is scored alongside. Corrected contrast I on the exclusive stratum is
**+0.0335** (CI99 [+0.0236, +0.0438], 14/14 units), against **+0.0660**
uncorrected: close to half of the original was memorisation.

**`allele.json` is kept as run.** The void number stays in the repository with
this entry pointing at it, because a rejected analysis is recorded rather than
deleted. `QC_G12_allele.md` §2.1 states the 97.93% / 0.00% split so the number
cannot be quoted without it.

**A second D029 defect, found at the same time and recorded separately in
`QC_G12_allele.md` §3.** D029's sign rule assumed the carrier and non-carrier
groups are symmetric. They are not: the 29 carriers share HLA-A\*02:01, while
the 23 non-carriers share only its absence and span 41 alleles — a figure
printed in D029's own table. Contrast II is therefore a weak replication test by
construction. This was knowable before the run and was not seen. It is recorded
as a defect in the rule, **not** as grounds to reinterpret a preregistered test
that the result fails; §4 of the QC document names the symmetric test that would
settle it instead.

---

## D029 — The allele-disjoint split is one-allele-held-out, and what to do about it · RESOLVED

**Opened and resolved:** 2026-10-07 · **Before any allele-arm result was visible**
**Depends on:** D001 (the preregistered secondary split), D028 (the matched-control precedent)
**Affects:** §9, §10, §20, §25 · **Blocks:** G13

**Decision: run D001's split exactly as preregistered, rename what it measures,
and add a matched control plus an allele-enriched stratum, because the split as
built holds out one allele rather than a disjoint allele set.**

### The naming is wrong, and the error is not cosmetic

D001 specified "an allele-disjoint split alongside the donor-disjoint split" and
`SPLIT.csv` implements it as `allele_disjoint_partition`: 23 units that do not
carry HLA-A\*02:01 against the 29 that do. **The two partitions are not allele
disjoint.** Measured in-repo:

| Quantity | Value |
|---|---|
| Alleles present in the 23-unit training partition | 41 |
| Alleles present in the 29-unit test partition | 36 |
| Test alleles **absent** from training | **5** — A\*02:01, A\*29:02, B\*27:02, B\*56:01, B\*57:01 |
| Test units with exactly one unseen allele | 23 of 29 |
| Test units with two unseen alleles | 6 of 29 |
| Mean fraction of a test unit's alleles unseen in training | **21.7%** |

So roughly four fifths of every test unit's HLA repertoire is represented in
training. Each test unit presents peptides from five or six alleles pooled, and
no deconvolution assigns a peptide to its restricting allele, so **the peptides
that could show an allele effect are diluted about fivefold by peptides from
alleles the model has already seen.** A real effect of holding out an allele
would appear attenuated by roughly that factor, and the split would understate
it. Reading a small difference from this split as "allele identity does not
matter" would be reading an attenuated design as a null result.

D001 was right that genotype had to be carried and that the split had to exist —
this entry does not reopen that. What it corrects is the claim the split can
support. It is a **dominant-allele-held-out** split, and that is what will be
reported. `allele_disjoint_partition` keeps its column name, because renaming a
frozen column would break the split freeze; the name is wrong and this entry is
where that is recorded.

### What is run

**1. P_AD — D001 verbatim.** Train on the 23 non-carriers, test on the 29
carriers. 5 of the 23 are an early-stopping holdout (same necessity and same
deviation as D028), so 18 units train.

**2 and 3. M_AD and M_AM — the matched pair.** Carriers and non-carriers are
each split platform-stratified (D025 makes stratification mandatory) under
`seed('allele_split')`:

| Pool | units | LTQ / Lumos |
|---|---|---|
| C_pool — carriers available for training | 15 (12 train + 3 val) | 7 / 8 |
| C_test — carriers held out | 14 | 7 / 7 |
| N_pool — non-carriers available for training | 15 (12 train + 3 val) | 7 / 8 |
| N_test — non-carriers held out | 8 | 4 / 4 |

M_AD trains on 12 non-carriers; M_AM trains on 12 carriers. Both are scored on
**both** held-out sets. Training size is equal, so the arms differ in whether
the training units carry the dominant allele and in nothing else.

| Contrast | test units | matched model | mismatched model |
|---|---|---|---|
| **I** | C_test (14 carriers) | M_AM | M_AD |
| **II** | N_test (8 non-carriers) | M_AD | M_AM |

Both are paired per unit, so the interval is a paired cluster bootstrap and
between-unit variance cancels. **The pattern is what identifies the cause, and
it is fixed here before the numbers exist:**

- **Both contrasts positive** → sharing the test units' allele class with
  training helps, in both directions. That is an allele effect.
- **Opposite signs** → one training set is simply the better one, and contrast I
  alone would have been read as an allele effect that is not there.

A single arm cannot distinguish these. This is the same failure D028 found in
D025, and it is the reason this entry exists.

**Arm-specific floors.** Each arm carries a composition-only LDA fitted on its
own training rows and scored on its own test rows, by the D002 method. D028
measured why: arm floors there ran 0.5917 to 0.6648 against the pooled 0.597,
and using the pooled figure would have reversed the ordering between two arms.

### The allele-enriched stratum

The fivefold dilution above is the design's main weakness, so a stratum is
preregistered that concentrates the peptides plausibly restricted by the
held-out allele. **It is defined using only the pooled training units, never the
held-out ones:** a sequence is *carrier-restricted* if it was observed in ≥2 of
the 15 C_pool units and in none of the 15 N_pool units, and
*non-carrier-restricted* with the roles reversed. 4,664 and 3,523 sequences
respectively.

**The definition was validated on units excluded from it** before being adopted:

| Stratum | reaches a C_test unit | reaches an N_test unit | per-unit rate ratio |
|---|---|---|---|
| carrier-restricted | 29.25% | 8.04% | **2.08** |
| non-carrier-restricted | 17.43% | 12.63% | **0.79** |

Carrier-restricted peptides turn up in held-out carriers at twice the per-unit
rate of held-out non-carriers, and non-carrier-restricted peptides go the other
way. The stratum tracks genuine carrier-linked restriction rather than peptide
privacy, which is the trap the first attempt fell into: carrier-*exclusive*
peptides without a recurrence requirement are **91.6%** of every carrier's
positives, because 79.9% of peptides are participant-private (D003). That
version was discarded before being preregistered, and is recorded here rather
than omitted.

Each eval is reported on all rows and on the stratum matched to the test units'
own class, with negatives subsampled 1:1 per unit under
`seed('allele_stratum_negatives')` so average precision stays on the same scale
as the primary. Both arms of a contrast are scored on identical rows, so pairing
holds.

**What the stratum is not.** Carrier-linked is not A\*02:01-restricted. The
stratum will also capture peptides restricted by alleles in linkage with
A\*02:01, and any other systematic difference between the carrier and
non-carrier groups. It raises the effect's concentration; it does not identify
the restricting allele. Nothing here is allele deconvolution.

### Recorded limits

1. **This cannot license §20 on its own.** Even both contrasts positive would
   show that peptide repertoires differ by HLA genotype in a way a sequence
   model detects — which is a weaker statement than allele-specific binding, and
   is also what the confounds shared by both groups would produce. G13 stays
   held after this analysis, not released by it.
2. **8 units** in contrast II. The sign is informative; its magnitude is not
   well determined.
3. **All three arms train on units inside the primary test partition**, as the
   transfer arms did. These models serve this analysis only and never §25, which
   was read once and is closed.
4. **The stratum analysis changes prevalence and set size**, so its absolute AP
   is not comparable to R9's. Only the paired within-stratum contrast is.

**Seeds.** `seed('allele_split')` for the pools, `seed('allele_valsplit')` for
the early-stopping holdouts, `seed('allele_init', i)` for weights,
`seed('allele_bootstrap')` for intervals, `seed('allele_stratum_negatives')`
for the 1:1 stratum negatives. Five replicate seeds per arm; per-unit AP is the
mean across them, as D027 fixed.

**Outcome, 2026-10-07 (`results/qc/QC_G12_allele.md`). VERDICT INCONCLUSIVE.**

The preregistered arm is clean and clear: trained on non-carriers, the model
scores the 29 carriers at a leakage-free lift of **+0.1064** over its own floor,
against +0.1015 and +0.1042 for the two cross-platform arms. **Holding out the
cohort's most common class-I allele costs nothing visible.** At the
whole-repertoire level the matched contrast puts the cost at **+0.0072**, CI99
[−0.0015, +0.0162] — an interval containing zero, exactly as the fivefold
attenuation above predicts.

The stratum designed to defeat that attenuation was **broken**, and in the
direction that flattered the hypothesis: see D030. Corrected, contrast I on the
carrier-exclusive stratum is **+0.0335**, CI99 [+0.0236, +0.0438], **14 of 14
units positive**, and it is not memorisation (zero by construction), not
recurrence (difference-of-differences against a recurrence-matched control
+0.0279, CI99 [+0.0067, +0.0472]) and not one training set being better
(measured directly at +0.0005, CI99 [−0.0081, +0.0092] over 22 units).

**But this entry's own sign rule rejects it.** Contrast II came out at −0.0131
on its exclusive stratum, so the signs are opposite — the branch this entry
assigned to "one training set is simply better". That premise is measurably
false here, which is recorded and does **not** convert a failed preregistered
test into a passed one. The rule's symmetry assumption was the defect, and D030
records that it was knowable in advance from the 41-allele figure in this
entry's own table.

**G13 stays held, as this entry said it would whatever the result.**

---

## D028 — Cross-platform transfer: the preregistered form is kept, and a matched control is added · RESOLVED

**Opened and resolved:** 2026-10-07 · **Before any transfer result was visible**
**Depends on:** D025 (preregistration), D005 (the confound), D027 (model → value)

**Decision: run D025 exactly as preregistered, and add a matched
within-platform control, because the preregistered form on its own cannot
distinguish a platform effect from a smaller-training-set effect.**

**What D025 preregistered.** "Train on the 25 LTQ units and test on the 27
Lumos units, then the reverse. ... If performance holds within platform and
collapses across, the §25 claim is substantially about instrument rather than
biology."

**The gap.** The preregistered text names the across-platform arms but never
names what "holds within platform" is measured against. The obvious candidate —
the primary endpoint, 0.7551 — is **not** a valid comparator: it was produced by
models trained on 42 units spanning *both* platforms and evaluated on 10 units
spanning both. An across-platform arm trained on ~20 single-platform units
differs from it in training size, training diversity *and* platform. If the
transfer number comes out lower, the preregistered design cannot say which of
the three caused it. Reporting the comparison anyway would be the error D025
was written to avoid: a confound measured against a yardstick that carries the
same confound.

**The addition.** Each platform's units are split in half by
`seed('transfer_halves')` = 952257691:

| | train half (A) | test half (B) |
|---|---|---|
| LTQ | 13 units | 12 units |
| Lumos | 14 units | 13 units |

Ten units are drawn from each A half for training (equalised, so the two
matched arms differ in platform and nothing else); the remainder of A is the
early-stopping validation set. Each trained model is then evaluated on **both**
B halves. That yields two contrasts from the same two trainings:

- **Contrast A — same model, different test platform.** One model, evaluated on
  held-out units of its own platform and of the other. Training is held
  identical; only the test platform moves.
- **Contrast B — same test units, different model platform.** One set of test
  units, scored by a model trained on its own platform and by one trained on the
  other. The test set is held identical; only the training platform moves. This
  contrast is **paired per unit**, so the interval is a paired cluster bootstrap
  and between-unit variance cancels.

Contrast A controls for the model, contrast B for the test set. Agreement
between them is what makes a collapse attributable to platform.

**Arm-specific floors replace the global 0.597.** The D002 floor was measured on
pooled data. Platform shifts composition (D025: 12-mers are 11.69% of LTQ
positives against 9.85% of Lumos), so the composition-only separability of a
cross-platform test set is not the pooled figure. Each arm therefore carries its
own floor: a composition-only LDA fitted on that arm's training rows and scored
on that arm's test rows, by exactly the D002 method. Lift is measured against
the arm's own floor, never against 0.597.

**Why this is an addition and not a substitution.** The preregistered arms are
run and reported first, with their numbers, whatever they are. The matched
control is labelled as added after preregistration and before any result was
seen — the ordering is in the commit history, and this entry was committed
before the run. It cannot select a favourable answer because it fixes the design
by seed and leaves no choice to make afterwards.

**What this analysis is not.** It does not remove the confound. No unit spans
both platforms (D005), so platform and participant stay perfectly nested and
nothing here recovers a platform-free estimate. It measures the confound's size.

**Outcome, 2026-10-07.** The matched control earned its place. The two
preregistered arms came in 0.055 and 0.044 below the primary endpoint, a gap
that the preregistered design alone could not have attributed; the matched
contrasts put the platform component of it at 0.04–0.06 and did so twice, once
with the model held constant and once with the test units held constant, the
two agreeing to within 0.01.

The arm-specific floors mattered more than expected. They range from 0.5917 to
0.6648 — a spread of 0.073 across arms, against the single pooled 0.597 the
analysis would otherwise have used. Against the pooled floor, LTQ → Lumos
(0.6959) and within-LTQ (0.7481) would have looked 0.05 apart in lift; against
their own floors they are 0.1042 and 0.0833, which reverses the ordering. The
pooled floor would have made the transfer arms look worse than they are and the
within-LTQ arm better.

That spread also produced the post-hoc diagnostic in QC_G12 §2.3: on the LTQ
half the CNN's cross-platform penalty is indistinguishable from the one a
composition-only linear model pays on the same units, while on the Lumos half it
exceeds it by 0.0261 with all 13 units in the same direction. Recorded as
post-hoc, because it was asked only once the floors were seen to move.

**Seeds.** `seed('transfer_halves')` for the halves,
`seed('transfer_valsplit')` for the early-stopping holdouts,
`seed('transfer_init', i)` for weights (a new purpose string, so no collision
with the cv or final-fit seeds), `seed('transfer_bootstrap')` for the intervals.
Five replicate seeds per arm, matching D027; per-unit AP is the mean across
them, as D027 fixed.

**Accepted cost.** The matched arms train on 10 units against the primary fit's
42, and all four arms train on units that fall inside the primary test
partition. Both are stated rather than worked around: these models are used for
this analysis only and never for the §25 endpoint, which was read once and is
closed.

---

## D025 — Platform stratification and cross-platform transfer · RESOLVED

**Resolved:** 2026-10-06 · **Evidence:** run-010 · **Escalates:** D005

**Decision: the split must be stratified by platform. A cross-platform transfer
analysis is preregistered as a secondary endpoint.**

**What changed.** D005 accepted the instrument confound as a limitation on the
grounds that no split over units can separate platform from participant. run-010
shows the peptides themselves carry a platform signature readable by a trivial
model: **composition-only AUROC 0.6451**, against a **0.5150** control
comparing random halves of units. Generic unit-to-unit variation gives almost
nothing; platform gives a third of the way to perfect separation from amino-acid
frequencies alone.

A visible mechanism: 12-mers are 11.69% of LTQ positives against 9.85% of
Lumos, consistent with different detectability across the mass range.

**Stratification is now mandatory rather than advisory.** Matched platform
proportions in every partition do not remove the confound — nothing can, since
no unit spans both platforms — but they stop the split from silently becoming a
platform split, which at this separability would be a substantial artefact
masquerading as generalization failure.

**The transfer analysis is the point.** Train on the 25 LTQ units and test on
the 27 Lumos units, and the reverse. This measures the confound directly instead
of inferring it. If performance holds within platform and collapses across, the
§25 claim is substantially about instrument rather than biology.

**Preregistered now, before any result is visible**, because it is the analysis
most likely to be reinterpreted as exploratory if it were run after seeing a
disappointing headline number.

**Outcome, 2026-10-07 (`results/qc/QC_G12_transfer.md`).** Run as written, with
the D028 matched control. **Performance does not collapse across platforms.**
LTQ → Lumos 0.6959, CI99 [0.6805, 0.7113]; Lumos → LTQ 0.7108, CI99 [0.6993,
0.7221]. Both lower bounds clear the D008 threshold of 0.647 and each arm's own
composition floor + 0.05. The collapse condition this entry specified is not
met, so the pre-committed reading *"the signal is substantially instrument, not
presentation"* does not apply.

A platform effect is nonetheless measured, at **0.04–0.06 AP**, from four
estimates across two contrasts with no interval containing zero. That is the
confound's size: D005 remains an accepted limitation, and this entry's purpose
was to measure it rather than remove it, which it did.

---

## D024 — Per-unit positive cap · RESOLVED

**Opened and resolved:** 2026-10-06 · **Status:** RESOLVED
**Evidence:** run-007 (`results/power/subsample_curve.json`), run-001 F2/F5, run-006

**Decision: cap each unit at 10,000 positives, sampled stratified by peptide
length, seed 20261006.** 520,000 positives total.

**Chosen from the precision curve, not the compute table**, as the decision
required. The estimand's variance is (between-unit + within-unit) / K. K is
fixed at 52 by the data, so a cap touches only the within-unit term:

| Cap | within-unit SD | within ÷ between | SD of the mean | marginal gain |
|---|---|---|---|---|
| 500 | 0.01664 | 0.305 | 0.00790 | — |
| 1,000 | 0.01085 | 0.199 | 0.00771 | +2.48% |
| 5,000 | 0.00536 | 0.098 | 0.00760 | +0.28% |
| **10,000** | **0.00359** | **0.066** | **0.00758** | **+0.26%** |
| 40,000 | 0.00184 | 0.034 | 0.00757 | +0.04% |

*(τ = 0.25; 52 units; 1:1)*

**Going from 10,000 to all 2.66M positives would improve the interval by
0.16%.** Within-unit noise is already 15× smaller than between-unit variation,
so the extra data is spent reducing a term that no longer matters.

**Why 10,000 and not 5,000.** The binding case is small between-unit variance,
where within-unit noise matters most. At τ = 0.10 the threshold is reached at
5,000; 10,000 gives a 2× margin against a τ we cannot measure until the model
runs, and costs 23.6 h of a 96 h budget against 11.8 h. Buying margin on the
one unknown parameter is worth 12 hours.

**An unanticipated benefit.** Every unit holds at least 39,991 sequences, so
all 52 clear the cap and it applies uniformly. That **equalises contribution
across units** — and `METHODOLOGY.md` limitation 3 records that unit sizes vary
5-fold, so pooled peptide-level statistics would otherwise be dominated by the
heaviest contributors. The cap removes that distortion as a side effect. It is
not why the cap was chosen, and it is recorded as a consequence rather than a
justification.

**Sampling rule: stratified by length, proportional to each unit's own
distribution.** Random sampling preserves the length mix only in expectation;
stratification preserves it exactly. Length is the strongest structural feature
of the set — 9-mers are 27.8% of the union — and letting it drift between units
would introduce a difference the model could learn that has nothing to do with
presentation.

**Preregistered.** Cap, rule and seed are fixed here, before the split is
locked and before any model is fit. Choosing any of them after seeing
performance would be selection.

**What this does not do.** It does not reduce the evidence about *units*, which
is what bounds every claim. It discards peptides, which are plentiful, to keep
units, which are not.

---

## D020 — Compute gate numbers

**Date opened:** 2026-10-06 · **Resolved:** 2026-10-06 · **Status:** RESOLVED
**Blocks:** nothing further · **Evidence:** run-002, `results/compute/benchmark.json`

**Question.** What are the §14 limits? The field had been empty since the
proposal was written, and I had declined twice to fill it on the grounds that a
compute budget is an institutional fact I cannot know.

**What changed.** The author asked for the numbers. The institutional budget is
still not mine to know, but the target machine is measurable and the
architecture is specified, so the limits are derived from measured throughput
rather than invented. Measured: 122,648 peptides/sec training throughput on
four cores with no GPU.

**Limits set.** In `SECTIONS.md` §14. In summary: 20 configurations, 100 epochs
with patience 10, 5 folds, 5 seeds for the selected configuration only, 150
total runs, 48 hours wall clock, 4 cores, no GPU, ~12 GiB peak extraction disk
(corrected from ~2 GB once container sizes were verified; see D021).
Worst-case grid cost ~31 hours against the 48-hour cap.

**Reduction ladder is preregistered** and ordered: seeds, then configurations,
then folds, then epochs. The prompt requires that a reduction be recorded
rather than silently applied; fixing the *order* in advance goes further, by
removing the discretion to choose which corner to cut once a budget is already
under pressure.

**What is never reduced:** the test partition, the split definition, the
allele-disjoint secondary analysis. These are the design. Cutting them to fit a
budget would be changing the experiment to afford it, which is the failure the
compute gate exists to prevent — so the gate must not become its instrument.

**Two findings the measurement produced incidentally.**

1. **No GPU is required.** The architecture is small enough that CPU throughput
   suffices, removing a hardware dependency the proposal left implicit.
   **SUPERSEDED by D022:** true at the 100,000-positive size assumed here, false
   at the ~1.9M the data actually yields.
2. **Streaming the containers is forced, not chosen.** 30 GB writable disk
   against a container set since verified at 107.53 GiB: the full set cannot be
   held.
   `DATA_SOURCES.md` presented stream-and-delete as the better of two options;
   it is in fact the only feasible one, which means the reproducibility cost
   recorded there — dependence on the publisher's continued availability — is a
   constraint we are under rather than a trade we made.

**Validity is bounded by the hardware.** Measured on this cloud machine. The
ladder and the structure port; the numbers do not. Different hardware requires
re-running run-002 and resetting the limits, and §14's status says so.

**Honest caveat on the measurement.** numpy over BLAS, not an optimised
framework, because the CPU-only framework wheel is blocked by the network policy
and the available wheel wanted 553 MB of GPU libraries for a machine with no
GPU. The figure is therefore an upper bound on time: a real framework should be
faster, so the budget has headroom rather than a shortfall. A FLOP-count
cross-check gave a floor of 2.7–27 s/epoch, which brackets the measured 9 s/epoch
from below as expected.

---

## D015 — Master prompt transcription: confirmed

**Date opened:** 2026-10-06 · **Confirmed:** 2026-10-06 by the author
**Status:** RESOLVED · **Blocks:** nothing

**The question had two halves, and only one was mine to answer.**

**Fidelity — verified, not asserted.** The committed `PROJECT_PROMPT.md` was
compared line by line against the brief as supplied: 128 content lines, zero
omissions, zero alterations, order preserved. Done mechanically rather than by
reading, because reading one's own transcription for errors is the least
reliable way to find them.

**Completeness — attested by the author, not verifiable by me.** Three lines in
the supplied text introduce content that does not follow it: "Maintain:" at the
end of *Data & Provenance*, "Each gate is:" in *Validation & QC Gates*, and
"Keep progress updates concise:" in *Communication*. Two sections also carry no
number, where 3 and 5 would fall. I could establish that these are present in
what was supplied; I could not establish whether the supply was complete. The
author has confirmed the transcription, so they stand.

**What that commits us to.** The truncated lines impose no requirement. A line
reading "Maintain:" with nothing after it obliges nothing, and no reader should
infer an unstated obligation behind it. The unnumbered sections keep their
positions; references elsewhere name them by title rather than by number, which
is why the restructure in D019 cites *Mapping Methodology* by name.

**If content was lost after all.** It is supplied as a new entry superseding
this one, not as an edit to `PROJECT_PROMPT.md`. The governing document stays
byte-stable so that every "master prompt" citation in this repository keeps
resolving to the text the work was actually done against.

**Why this was worth an entry rather than a quiet fix.** The tempting move was
to repair the three lines by inferring what they meant — a list of artifacts to
maintain, a PASS/FAIL enumeration, an update format. Each inference would have
been plausible and unfounded, and would have put words in the governing
document that its author did not write. That is the same failure as imputing a
genotype or inferring a class from a filename, applied to the project's own
charter.

---

## Ratified departures — D016 to D019

Ratified by the author in session on 2026-10-06, on the instruction "ratify the
departures". Each had been applied before being recorded, which is the failure
`PROJECT_PROMPT.md` §9 exists to prevent; ratification closes the procedural
gap but does not erase it, and the record keeps both.

Statuses use the prompt's §1 vocabulary. Two are **PERMANENT**: standing rules
that govern all future work rather than one-time choices. Two are **RESOLVED**:
closed events that need no further action.

---

### D016 — Approximate matching prohibited on every identifier join

**Status:** PERMANENT · **Ratified:** 2026-10-06 · **Governs:** all mapping gates

**What it departs from.** The prompt's *Mapping Methodology* section requires
"approximate/fuzzy matching rules" to be defined. This project defines them as
prohibited, which is a narrower answer than the field anticipates.

**Why.** The identifier space is dense in near-neighbours. Acquisition
filenames differ by one character between genuinely different runs; participant
identifiers differ by one digit between different individuals. Any
edit-distance threshold loose enough to repair a transcription error is also
loose enough to merge two distinct entities, and the merge is silent and
unrecoverable downstream. The prompt's own rule — never silently force an
ambiguous match — is better served by refusing the match than by tuning a
threshold.

**What it commits us to.** A non-empty unmatched set is a normal, reportable
outcome rather than a defect to be eliminated. Near-misses are recorded as
adjudication candidates with both normalized keys and the edit distance, and
stay unmatched until a logged decision resolves them. No matcher may promote a
near-miss.

**As PERMANENT, this applies to mappings not yet written.** Any future join
added to this project inherits the prohibition unless a new entry supersedes
this one.

---

### D017 — Proceeding with run-001 while G1 was failing

**Status:** RESOLVED · **Ratified:** 2026-10-06 · **Scope:** that run only

**What it departs from.** `PROJECT_PROMPT.md` §1: "Do not proceed to the next
major stage until the current stage has passed its QC gate." G1 was failing —
retrieval was blocked by network policy — and the design analysis that followed
belongs to §16/§25 territory, well downstream.

**Why it was defensible.** The analysis required no project data, so it could
not be contaminated by the data it preceded. It was cheap, and it was run
before the expensive extraction stage precisely so it could still change the
plan. It did: it found the primary hypothesis near-unfalsifiable and the stated
precision mechanism inert.

**Why it was still a departure.** The gate rule is unconditional as written,
and the alternative — waiting — was available. The run record originally
described the stage as "not a pipeline stage; no gate", which sidestepped the
question rather than raising it. That framing has been corrected and the
rejected alternative is now recorded in the run's research record.

**Scope of this ratification.** This covers run-001 only. It is **not** a
standing permission to run downstream analyses while an upstream gate is
failing; a further instance needs its own entry.

---

### D018 — Required field sets omitted, then repaired

**Status:** RESOLVED · **Ratified:** 2026-10-06 · **Scope:** closed

**What happened.** `SECTIONS.md` was written with eight of the nine
per-section fields the prompt §1 requires, omitting "Why the method is needed"
across all seventeen sections and renaming two others. `RUN_LOG.md` omitted
three of the prompt §4 research-record fields. Neither omission was deliberate
and neither was recorded.

**Why it matters more than the missing text.** The omitted field is the
justification for each method choice — the part of the record that explains why
an approach was taken rather than what it does. Dropping it quietly is how a
framework erodes into whatever the implementer found convenient, which is the
specific failure the prompt's §9 is written against.

**Repair.** All nine fields restored across all seventeen sections with
substantive justifications; the three research-record fields added to run-001,
including the alternative rejected in favour of the D017 departure. Verified by
audit rather than inspection: field counts checked programmatically against the
prompt's list.

**Retained in the record** rather than silently corrected, so the omission and
its repair are both visible.

---

### D019 — METHODOLOGY.md restructured to the prompt's eleven-field format

**Status:** PERMANENT · **Ratified:** 2026-10-06 · **Governs:** document structure

**What changed.** All seven mappings are now documented under the prompt's
eleven *Mapping Methodology* fields, in its order, as headings. The numbered
join, normalization and status schemes of the earlier draft are removed.

**Two compressions, both flagged in the file.** Shared normalization
conventions are stated once rather than repeated under all seven *normalization
rules* fields, which would duplicate the same eight lines seven times. The
`M1`–`M7` tags survive as cross-reference labels carrying no meaning, so that
`FLOWCHART.md`, `REPORT.md` and `DATA_SOURCES.md` can name a specific mapping.

**Cost paid.** The restructure broke twelve cross-references across three
files, since the earlier section numbers no longer exist; all twelve were
repointed to named sections, and the flowchart's status diagram was reconciled
to the per-mapping definitions.

**As PERMANENT, this fixes the document's format.** Any mapping added later is
documented under the same eleven fields. A future change of format needs a new
entry superseding this one.

---

## Conventions

- Entries are append-only. A superseded decision gets a new entry that cites
  the old one; the old entry is edited only to change Status and add the
  pointer.
- Rejected options stay in the record with their reason (§6 of the master
  prompt: never delete rejected analyses).
- No entry moves to RESOLVED on reasoning alone. Each lists what must be
  computed in-repo first, and cites the artifact that satisfies it.
- Counts quoted from external metadata are provisional until recomputed from
  the retrieved file and recorded in the data registry.
