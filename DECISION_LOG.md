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
| D003 | Cross-split sequence leakage. **RESOLVED** — keep shared sequences, report the leakage-free subset as a sensitivity analysis. 14.59% of test positives are seen in training under unit-disjoint splitting. See entry below | G5, G6 |
| D004 | Confidence threshold. **RESOLVED as a no-op** — 99.29% of the union is at the top level, so re-filtering removes 0.7%. Must be re-framed around the PeptideScores table if purity control is wanted | G4 |
| D024 | Per-unit positive cap. **RESOLVED: 10,000 per unit, length-stratified, seed 20261006.** Chosen from a precision curve; costs 0.16% of attainable precision | G4, G6 |
| D025 | Platform stratification and cross-platform transfer. **RESOLVED** — stratification mandatory; transfer analysis preregistered. Instrument is learnable from composition at AUROC 0.645 vs 0.515 control. See entry below | G6 |
| D005 | Instrument confound. **RESOLVED — accepted as a limitation**; total confound, cannot be corrected. See entry below | G3, FAIL accepted |
| D006 | Predictor training-set overlap. **RESOLVED as a protocol**: no predictor enters §18 without its training list obtained; handling fixed per outcome; §18 may never be promoted while any predictor is UNVERIFIABLE. See entry below | G11 |
| D007 | Minimum-N gate. **RESOLVED — clears overwhelmingly**: 2,658,972 eligible positives. The confirmatory arm is not data-limited | G4 |
| D008 | Decision rule for §25. **RESOLVED: reject if the lower bound of a nominal-99% cluster-bootstrap interval exceeds 0.647** (floor 0.597 + 0.05). Nominal 99% because 95% delivers only ~89% actual coverage. See entry below | closed |
| D009 | Preregistration freeze. **RESOLVED** — annotated signed-content tag pushed to the remote, carrying every artifact checksum. Limits of what it proves stated explicitly. See entry below | G6 |
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

**Decision: an annotated git tag at the freeze commit, carrying the SHA-256 of
every frozen artifact, pushed to the remote.**

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
