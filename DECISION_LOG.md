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
| D035 | **Freeze reopened deliberately** to add NetMHCpan 4.1 as a third §18 arm. Its training data is published openly (12,081,588 peptides) and was measured before the software arrived: 9.22% of test positives, 3.32% of negatives, a 2.8:1 bias that is weaker than MHCflurry's ~7:1 and weakens D006's one-direction argument for this arm | reopens the freeze |
| D036 | Admit MixMHCpred 3.0 and NetMHCpan 4.2. All five predictors are quantified `OVERLAPPING`, but 4.2 has seen 20.74% of our positives AND 16.20% of our negatives (bias 1.3:1), so D006's one-direction argument fails for it. §18 moves to TWO row sets: pairwise primary, plus a common set, because an all-naive set would delete 17.2% of rows from every other contrast | extends D035 |
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

## D040 — NetMHCpan §7(v) consent requested; the licence grant is not consent · **RESOLVED — CONSENT GRANTED 2026-10-12, see D051** · (D048 precomputed the withdrawal, now retired)

**Opened:** 2026-10-11 · **Acts on** L26 in `LIMITATIONS.md`, opened by D037

**Decision: request DTU Health Tech's written consent to publish the §18
benchmark, and record both what was asked and what happens on either answer.**

### 1. Why the licence grant does not already settle it

The academic licence for NetMHCpan-4.1 was issued on 2026-10-07 by the DTU
Health Tech Package Manager. **That grant is not consent under §7(v)**, for
three reasons, recorded because the opposite reading is a natural one:

- **§7(v) is a term inside the licence that was granted.** The grant message
  states that the licence terms are attached; those attached terms carry the
  restriction. A grant cannot also be consent to an exception carved out
  within itself.
- **The grant is automated** — "This is a computer generated message, please do
  not reply!" No person considered this publication.
- **It predates the benchmark.** It cannot consent to results that did not yet
  exist.

A licence to *use* a tool implying permission to publish results of that use is
a reasonable intuition and matches how the field behaves. The clause explicitly
carves benchmark publication out, so the intuition does not settle it.

### 2. What was asked

Sent 2026-10-11 to `health-software@dtu.dk`, the address DTU's service page
names for software licensing, copying the automated address the grant came
from. The request quotes §7(v), references the 2026-10-07 grant so DTU can
match it to their record, and names precisely what is published:

- the mean average precision of 0.5472 on 165,574 rows common to five systems;
- the per-peptide `Score_EL` and `%Rank_EL` values for 199,978 rows in
  `results/predictors/netmhcpan_4_1_test_scores.csv`.

It also states what is **not** published — the software, its code, its model
files and its verbatim stdout, the last deliberately excluded under D037 — and
volunteers the confound in the tool's favour: the comparison cannot separate
model quality from cohort-specific training, which `REPORT.md` and L15 already
say. The citation the service page requires is given.

### 3. What happens on each answer

| Answer | Action |
|---|---|
| **Consent given** | L26 closes. Record the reply date and the granting address here. Nothing in the repository changes |
| **Consent refused** | Withdraw the NetMHCpan 4.1 arm: `results/predictors/netmhcpan_4_1_test_scores.csv`, its rows in `predictor_comparison_all.json`, `contamination_all.json` and `comparison_with_predictors_all.csv`, the §18 and R14 text, and F13. **§18's finding survives**: that the published predictors span 0.0046 AP rests on MHCflurry 2.0.0, MHCflurry 2.3.0 and MixMHCpred 3.0 without it. Re-freeze and record the new numbers |
| **No reply** | L26 stays open with the request on the record. Not silently closed by the passage of time |

### 4. The DOI waits for the answer

A Zenodo deposit is immutable. Archiving before the answer risks permanently
publishing a tree that then has to lose an arm, so no release is tagged until
DTU replies or the arm is withdrawn. Logging in to Zenodo and enabling the
repository toggle are both reversible and do not mint anything; **publishing a
release is the irreversible step.**

**RESOLVED as to the action** — the request is sent and its terms are on the
record. The outcome is external and is tracked at L26 until it arrives.

---


## D039 — D038 reversed for eight of nine documents; a reference gate added · RESOLVED

**Opened:** 2026-10-11 · **Supersedes D038 in part** · **Requested by the
project owner** after the dangling-reference defect was reported

**Decision: ship eight of the nine documents D038 untracked, keep `HANDOVER.md`
withheld, extract a standalone `LIMITATIONS.md`, and add a gate that fails when
a shipped document cites a file that is not shipped.**

D038 is not edited. It was right about its own limits and said so; this entry
records that its central trade-off did not survive contact with the published
repository.

### 1. Why D038 was reversed

**The repository cited documents it did not ship.** A reader following
`README.md` was told the limits in `REPORT.md` §19 were "not boilerplate — read
them before reusing any number here", and `REPORT.md` was not there. The
repository withheld the only statement of its own limits while publishing every
number those limits qualify. That is worse than a broken link.

**The findings were already public anyway, exactly as D038 §3 predicted.** The
live `README.md` on `main` serves 0.7551, 0.6852 and 0.0046 unauthenticated,
alongside 180 tracked files under `results/` — all seven figures, fifteen QC
gate records, `endpoint.json`. Withholding `REPORT.md` protected nothing and
cost the caveats. **Shipping it reduces exposure rather than increasing it.**

**`LICENSE`, `LICENSE-docs` and `CITATION.cff` all cited an unshipped
`THIRD_PARTY_NOTICES.md`.** `LICENSE-docs` grants CC BY 4.0 over "the result
artifacts in `results/`", which includes `mixmhcpred_3_0_test_scores.csv`, and
pointed at that file for the third-party carve-out. **The public repository was
therefore granting commercial reuse over MixMHCpred-derived output with the
restricting document invisible.** That is a licence exposure, not a tidiness
defect, and it is the single most consequential finding of this audit.

### 2. What was shipped, and the safety check that preceded it

Shipped: `METHODOLOGY.md`, `REPORT.md`, `RUN_LOG.md`, `SECTIONS.md`,
`THIRD_PARTY_NOTICES.md`, `POWER_ANALYSIS.md`, `PROJECT_PROMPT.md`,
`ENVIRONMENT.md`.

All nine were scanned for publication hazards before any was shipped: secrets,
tokens, keys, personal identifiers, institutional affiliation, absolute paths,
cost and credential material. **Eight were clean on every axis.**

Withheld: **`HANDOVER.md`** alone — the only one with no scientific content and
the only one the scan flagged. It records the project's cloud spend ($50.05 of
a $100 allowance, ~$0.70 per turn) and a `GH_TOKEN` `repo`-scope instruction.
The four open issues it lists are all recorded in `DECISION_LOG.md` and
`SECTIONS.md`, so withholding it loses nothing. Its three references were
rewritten.

**D038 §2 still holds and is not reversed by this entry:** `HANDOVER.md`, and
everything D037 and D038 untracked, remain recoverable from this repository's
history by anyone who clones.

### 3. `LIMITATIONS.md`

Twenty-six limitations, each with a status (permanent / open / resolved), its
impact, and what would close it, extracted from `REPORT.md` §19 and grouped by
what they prevent the study claiming. Shipped unconditionally so that no future
decision about the report can again publish the numbers without them.

It records that three of its four groups converge: **a second cohort** closes or
advances L1, L8, L14, L15, L16 and L22 — the instrument confound, the
single-context ceiling, the allele result, the architecture-versus-cohort
question, the headline negative finding, and the only reader-dependent step in
the report. No further analysis of PXD024871 reaches any of them.

### 4. A stale limitation found while extracting it

`REPORT.md` §19 claimed **"Two predictors named in §18's own input list were
never obtained."** R14, in the same document, reports all four predictors on a
common row set. The claim was true when written and **false as of R14**; D035
and D036 obtained both. The report contradicted itself.

Marked `[SUPERSEDED]` in place with the correction and the date, **not
deleted** — the same treatment D030 gave its void contrast. Carried into
`LIMITATIONS.md` as L18, status `resolved`.

Four further stale references were found the same way and annotated rather than
deleted: `CONTAINER_RUN_MAP.csv`, `PEPTIDE_OBSERVATIONS.parquet`,
`TRAIN.csv`, `VALIDATION.csv`, `TEST.csv`, `CNN_PREREGISTRATION.md`,
`cnn_config.json` and
`training_log.csv` were all **planned in the specification and never produced**.
Each now says so, and says what serves its role. The gap between a plan and what
was built is evidence about the project.

### 5. The gate: `scripts/check_references.py`

Extracts every file reference from every shipped `.md`, `.cff` and `.ipynb`,
resolves it, and exits non-zero naming each one that does not resolve to a
**tracked** file. Tracked, not merely present on disk: a file in the working
tree but untracked is in nobody else's clone, and that distinction is the whole
defect.

`--selftest` builds a tree with a real dangling reference in each of the three
syntaxes and asserts the gate fails on it, and that a consistent tree reports
nothing. **A gate only ever observed to pass is untested.**

**Two rounds of its own false positives are worth recording**, because both
would have made it useless:

1. The first version reported **120** findings by treating prose mentions,
   `...` abbreviations and directory links as broken paths. Real defects would
   have been buried. Corrected: links resolve relative to the citing file;
   backticked prose resolves by basename anywhere in the tree.
2. The second reported `model/endpoint.json` as missing — prose writes path
   fragments relative to the directory under discussion. Corrected with
   component-boundary suffix matching.

The honest count was **44**, not 120.

Deliberate absences are **declared, not suppressed**: `DECLARED_ABSENT` maps 16
targets to a reason, the gate prints every one on each run, and anything not in
that map fails. Adding an entry is a decision and belongs here.

### 6. `.zenodo.json`

Added, with the dual licence, keywords, and `related_identifiers` pointing at
PRIDE **PXD024871** and the four papers. **No DOI is minted yet**: linking
Zenodo and publishing a tagged release are the owner's to do. A Zenodo deposit
is immutable, which is why it waits for a clean gate. The concept DOI, version
DOI, tag and commit will be recorded in a later entry.

**As RESOLVED, this fixes the dangling-reference defect and the licence
exposure.** No result, score, model or number was altered. The preregistered
digests are unmoved.

---


## D038 — Nine documents untracked at the owner's instruction · RESOLVED

**Opened:** 2026-10-07 · **Requested by the project owner**, explicitly and
after the limitation in §2 below was put to them twice · **Extends:** D037

**Decision: untrack nine documents so they do not appear in the published tree.
They remain on disk and in this repository's history; the limitation that
follows from that is recorded, not worked around.**

### 1. What was untracked

`METHODOLOGY.md` · `REPORT.md` · `RUN_LOG.md` · `SECTIONS.md` ·
`THIRD_PARTY_NOTICES.md` · `POWER_ANALYSIS.md` · `PROJECT_PROMPT.md` ·
`HANDOVER.md` · `ENVIRONMENT.md`

Internal and working documents, plus the findings. Of the nine, one contains
material that is personal rather than scientific: `HANDOVER.md` records the
project's cloud spend and a credential workflow. The rest are withheld as
internal, or as a result held pending submission.

### 2. What this does not do, stated plainly

**Untracking removes a file from the published tree. It does not remove it from
the repository.** Thirty-three commits carry `REPORT.md` with the primary
endpoint in it; every one of the nine is recoverable with `git log -p` or
`git cat-file -p <commit>:<path>` by anyone who clones. The published tree is a
closed door, not a locked one.

This was put to the project owner before the change and again after, with the
two alternatives that do close it: a fresh repository with no shared history, or
rewriting this one's history with `git filter-repo`. The second was advised
against here, because it invalidates `f7550f54`, `b83a741b`, `21048535` and the
other commit anchors cited throughout these documents — the preregistration's
"committed before any model was trained" claim rests on exactly those SHAs.

The owner chose untracking knowing this. **That is a legitimate choice** — most
readers of a public repository never open its history — and it is recorded here
so that no future reader mistakes the published tree for the whole repository.

A fresh-history public tree **was** built in parallel and verified (171 files:
the frozen dataset, 28 scripts and a reduced verifier, no results). It was not
pushed: the credential for the destination repository was never granted to the
session. It is not part of this repository.

### 3. What stays published, and still carries the findings

`REPORT.md` is untracked, but `DECISION_LOG.md` — this file — along with
`README.md`, `FREEZE_RECORD.md`, `CITATION.cff` and the whole of `results/`
remain tracked, and all of them quote the primary endpoint and the §18
comparison. The owner was told this. **Untracking `REPORT.md` therefore does not
hold the findings back**, and nothing in this entry should be read as claiming
it does. It removes nine documents from the tree; that is its whole effect.

### 4. Consequences handled

- `scripts/freeze.py --verify` reads `REPORT.md` (checks 3 and 4) and
  `SECTIONS.md` (check 6) **from disk**, so it still passes for anyone holding
  the full tree, and fails on a clone. `README.md` says so rather than leaving
  it to be discovered.
- References to the nine from still-published files were **left as written**.
  Editing a methods document to erase its siblings is the quiet repair §2 of the
  master prompt forbids. `README.md` carries a "Documents not published here"
  section instead, so the references resolve to an explanation.
- `LICENSE`, `LICENSE-docs` and `README.md` pointed at `THIRD_PARTY_NOTICES.md`
  for the predictor licences. Those pointers were repaired in place and the
  predictor citations now route through `CITATION.cff`, which carries all three.

**As RESOLVED, this fixes what the published tree contains.** It changes no
number, no artifact and no conclusion. The preregistered digests are unmoved.

---


## D037 — Public release: what is withheld, and one licence clause that is not resolved · RESOLVED

**Opened:** 2026-10-07, when the project owner decided to make the repository
public · **Requested by the project owner** · **Status: RESOLVED as to what this
repository does; one external consent is OUTSTANDING and is recorded as such.**

**Decision: prepare the repository for public release by withholding exactly
three classes of file, adding the standard files a public repository needs, and
recording — rather than quietly accepting — a licence clause that the §18
benchmark may breach.**

### 1. What is withheld, and why

| Withheld | Reason | What replaces it |
|---|---|---|
| `PXD024871_CNN_Experiment_Proposal.md` | Internal T-A4 document, headed "not yet preregistered or executed". Publishing it beside the preregistered work it became invites the reading that the two are one artifact. | `...STUB.md`: title, size, SHA-256 `56b690ad…`, last content commit `4350e280`, and the one constraint from it that shaped the repository's structure. |
| `results/predictors/netmhcpan_raw/`, `mixmhcpred_raw/` (37 MB) | Verbatim stdout of two academically licensed tools. Of everything here, republishing a tool's literal output comes closest to redistributing the tool. | The per-peptide **score** CSVs stay committed: they are the evidence behind §18 and are ordinary derived results. |
| `data/derived/TEST_PREDICTOR_OVERLAP_2_0_0.csv`, `..._2_3_0.csv` | Superseded duplicates of the five-predictor-era names, **byte-identical** — `eb1d22e2…` and `100816504c…` respectively. | The surviving `..._MHCflurry_2_0_0.csv` and `..._MHCflurry_2_3_0.csv`, hash-for-hash. |

Nothing was deleted from disk. All three classes remain in the working tree,
gitignored with the reason stated inline in `.gitignore`. §6 of the master
prompt forbids deleting rejected analyses; it does not require publishing an
internal proposal, and the distinction is the stub.

### 2. The licence clause this does not fix

The NetMHCpan 4.1 academic licence, §7, states that the licensee may not
"publish any results of benchmark tests run on the Product to a third party
without HEALTH's prior written consent." **§18 is a benchmark of NetMHCpan 4.1
and reports its average precision.** On a plain reading, making this repository
public is publishing that benchmark to third parties.

This was found by reading `netMHCpan-4.1_license.txt` as shipped with the
package — which is also the licence check that `DATA_SOURCES.md` S6 says must
precede any predictor output entering the repository. **That check had not been
performed when the output was committed.** The provenance records in
`data/raw/S6/provenance.jsonl` carried a one-line licence summary per file, but
no clause-level reading. The gap is recorded here rather than backdated.

Three things are true at once and all three belong on the record:

1. The clause says what it says.
2. Publishing NetMHCpan benchmarks is near-universal practice, including in the
   MHCflurry 2.0 paper, which benchmarks against NetMHCpan 4.0 in its abstract.
   That bears on whether the clause is enforced. It does not establish consent,
   and no consent has been sought.
3. The same licence's §10 requires that references to the software "for
   crystallographic computations" cite the manual — boilerplate from an
   unrelated package. The document is generic, which is evidence about its
   drafting and not a permission.

**Not resolved by analysis.** `health-software@dtu.dk` is the contact named on
the service page. The options — ask first, publish the other four arms, or
proceed on practice with the notice on the record — are set out in
`THIRD_PARTY_NOTICES.md` §1 and belong to the project owner, not to this entry.

A second carve-out **is** resolved: MixMHCpred's licence §2.1 permits providing
results "for academic non-commercial purposes only", which CC BY 4.0 cannot
widen. The MixMHCpred-derived files are therefore excluded from this
repository's CC BY grant, stated in `THIRD_PARTY_NOTICES.md` and in `README.md`.
MHCflurry is Apache-2.0 and carries no such restriction.

### 3. Licensing and standard files

MIT for `scripts/` and `notebooks/`; CC BY 4.0 for the documents, figures and
derived tables, at the project owner's election. The CC BY legal code in
`LICENSE-docs` was **retrieved** from creativecommons.org on 2026-10-07
(SHA-256 `9ba9550a…`) and embedded verbatim rather than reconstructed from
memory, because a licence written from memory is not a licence.

Added: `README.md`, `LICENSE`, `LICENSE-docs`, `CITATION.cff`,
`THIRD_PARTY_NOTICES.md`, `.gitattributes`.

Every citation in `CITATION.cff` and `THIRD_PARTY_NOTICES.md` was verified
against PubMed or the PRIDE API, which caught a fabrication in the first draft:
the PXD024871 deposit title had been written from memory and was **wrong**. The
PRIDE API gives "Immunopeptidomics-guided warehouse design for peptide-based
immunotherapy in chronic lymphocytic leukemia", submitter Annika Nelde, and
names the dataset publication — Nelde et al., Front Immunol 2021;12:705974,
doi 10.3389/fimmu.2021.705974. **That incidentally supplies S7, which
`DATA_SOURCES.md` has carried as never retrieved for the whole project.**

### 4. Two defects fixed in passing

**`.gitattributes` nearly broke the freeze for everyone but me.** The first
draft set `* text=auto eol=lf`. Python's `csv` module writes CRLF, so 67 derived
tables and score files are genuinely CRLF and were hashed that way; converting
them on checkout would have made `freeze.py --verify` fail on every clone while
passing on the machine that wrote the manifest. The committed file sets `* -text`
and says why. **This is the third instance of the project's recurring failure
mode** — a check that passes locally for a reason that does not travel — after
`TEST_LEAKFREE` and D029/D030. The standing lesson from D030 generalises:
verify on a fresh clone, not only in place.

**`FILE_MAP_REJECTS.csv` was 0 bytes, with no header.** A reader could not tell
"no rejects" from "this stage crashed", while M1's gate line asserted the
emptiness the file itself could not evidence. `phase_a_mapping.py`'s `write()`
took its header from `rows[0]` and wrote nothing when there were no rows. Fixed
at the source — `write()` now takes explicit `fields` — and the artifact
rewritten to exactly what the patched script produces, so script and artifact
agree. Zero rejects remains the correct and recorded result.

### 5. Verified before release

No secret, token, key or personal email address appears in any tracked file;
the `AKIA`-prefixed hits a scanner reports are peptide sequences. The three
predictor binaries live outside the repository tree and none is redistributed.
Participant identifiers, HLA genotypes and peptide sequences are reproduced only
as the public PRIDE deposit publishes them; `THIRD_PARTY_NOTICES.md` §3 notes
that genotype and immunopeptidome data are individually distinguishing in
principle, and that this repository adds nothing identifying and attempts no
re-identification.

**As RESOLVED, this fixes what the public repository contains.** The outstanding
item is external: DTU's answer, or the project owner's decision to proceed
without it. Neither changes a number.

---


## D036 — Two more predictors, and how the §18 row sets must change · RESOLVED

> **Pointer, added 2026-10-12 by D050:** the four row counts in the row-set
> table below are each 20 rows high. They were projected from the overlap lists
> before scoring was run, and did not yet carry the ambiguity-code exclusion.
> The corrected counts are in D050. No decision in this entry depends on them.

**Opened:** 2026-10-07, **before any MixMHCpred or NetMHCpan 4.2 score existed**
**Extends:** D035 (which reopened the freeze for NetMHCpan 4.1 only) · **Requested by the project owner**

**Decision: admit MixMHCpred 3.0 and NetMHCpan 4.2, and report §18 on TWO row
sets rather than one, because a single all-naive row set makes every comparison
pay for the most contaminated predictor in the panel.**

### Three claims in D033 and this log were wrong, all in the same direction

| Claim | Reality |
|---|---|
| "MixMHCpred … distributed via `raw.githubusercontent.com`, which this environment's proxy refuses" | **False.** That host returns 200 on any real file path; the bare host was tested and the result generalised. The repository clones normally through the session's git proxy |
| MixMHCpred "leans `UNVERIFIABLE`" (said in session) | **False.** Its training data is published as Additional file 2 of the paper — 2,557,766 rows, retrieved and registered |
| NetMHCpan training data not obtainable (D006/S6) | **False**, for 4.1 and 4.2 alike; both are open supplementary material |

**The pattern is one error repeated, not three errors.** Each time the cheapest
URL was tested rather than the one that mattered, and a negative result was
generalised to "unavailable". D033 made it about github.com; this entry makes it
about `raw.githubusercontent.com`. It is recorded as a pattern because the fix
is a habit, not a correction: **probe the specific artifact, never the host.**

### M7, all five predictors, one method (`contamination_all.py`)

The earlier `predictor_contamination.py` covered MHCflurry only and did not
split the overlap by label. It is kept as QC_G11 used it; this supersedes it.

| Predictor | train pos | train neg | our positives seen | our negatives seen | bias |
|---|---|---|---|---|---|
| MHCflurry 2.0.0 | 556,234 | 50,315 | 8.29% | 1.20% | 6.9 : 1 |
| MHCflurry 2.3.0 | 514,286 | 181,294 | 9.11% | 1.16% | 7.9 : 1 |
| NetMHCpan 4.1 | 387,475 | 11,693,931 | 9.22% | 3.32% | 2.8 : 1 |
| **NetMHCpan 4.2** | 440,390 | 12,741,099 | **20.74%** | **16.20%** | **1.3 : 1** |
| MixMHCpred 3.0 | 354,675 | 2,018,404 | 10.36% | 3.33% | 3.1 : 1 |

All five: `OVERLAPPING`, quantified. None needs the `UNVERIFIABLE` rule.

**NetMHCpan 4.2 is a different kind of comparator and must be labelled as one.**
It has seen **one in five of our positives and one in six of our negatives**, at
a bias of 1.3:1 — very nearly symmetric. D006's argument that contamination can
only flatter a predictor, which makes a CNN win conservative, **does not hold for
4.2 at all**: having been trained to reject one sixth of our decoys is help, not
handicap. Its larger decoy pool is the cause — 12.7M random-proteome negatives
against a set-C construction also drawn from the human proteome.

### The row-set problem this creates

D033 fixed the primary as rows naive to **both** compared systems. With five
predictors the natural extension is rows naive to all of them, and that extension
is a trap:

| Row set | rows | prevalence |
|---|---|---|
| CNN + both MHCflurry (the published §18 primary) | 175,544 | 0.440 |
| + NetMHCpan 4.1 | 170,648 | 0.441 |
| + MixMHCpred 3.0 | 165,594 | 0.440 |
| + NetMHCpan 4.2 | **141,276** | 0.443 |

**Admitting 4.2 would delete 29,372 rows — 17.2% — from every other
comparison**, including the CNN-versus-MHCflurry contrast already reported in
R13, purely because a fifth predictor saw them.

### Decision: two row sets, both reported

1. **Pairwise primary.** Each CNN-versus-X contrast runs on the rows naive to
   the CNN and to **X alone**. This is the largest valid row set for that
   contrast and does not let one predictor's contamination shrink another's
   evidence. Predictors are *not* mutually comparable across these sets, and
   that is stated wherever they appear.
2. **Common row set.** All five on the 141,276 rows naive to everything, where
   they are directly comparable to each other and to the CNN. Smaller, and the
   price of comparability.

Neither is "the" answer: the first maximises power per contrast, the second
maximises comparability, and reporting one without the other would hide the
trade. Prevalence stays at 0.440–0.443 throughout, so AP remains on one scale.

### Status and what is still missing

**MixMHCpred 3.0**: repository cloned (113 MB), training data registered
(sha256 `8101609a…`), free for academic use. Scoring can proceed.

**NetMHCpan 4.2**: training data registered (sha256 `243a3075…`), **software
not obtained.** The 4.1 licence the owner was granted does not cover 4.2; it
needs a separate `sw_request` submission. Until then 4.2 appears in the
contamination table and **in no comparison**, which is recorded here rather than
left to be noticed.

### Outcome, 2026-10-07 (`results/qc/QC_G11_four_predictors.md`)

**The two row sets were worth separating, and they agree.** Pairwise contrasts
run +0.1261 to +0.1345; common-set contrasts run +0.1373 to +0.1418. The
pairwise numbers are slightly smaller because their larger row sets retain
peptides the *other* predictors had seen, which are easier for everyone. No
conclusion turns on the choice, which is the outcome that makes reporting both
cheap and the omission of either indefensible.

**The finding neither row set was designed to produce: the four predictors
converge.** They span **0.5434 to 0.5479 — 0.0046** — on the common set. Three
groups, three training corpora, three architectures, one trained on 12 million
peptides, agreeing to within half a percentage point and differing from the CNN
together.

**That weakens the architectural reading of §18 considerably.** If the CNN were
a better model of presentation, the four would spread by capability and the
strongest would close some of the gap. They cluster instead, 0.14 below a model
trained on this cohort's own instruments, protocol and negative construction.
Four independent tools agreeing with each other and disagreeing with the CNN is
what a task-and-distribution advantage looks like, not a modelling one. QC_G11's
original §4 caveat was right and is now better evidenced than when it was
written with two predictors.

**NetMHCpan 4.2 remains unscored.** Its contamination profile (20.74% / 16.20%,
bias 1.3:1) would also have made it the weakest comparator of the five for
reasons unrelated to its quality, so the missing licence costs less than it
would for any other arm.

---

## D035 — Reopen the freeze for a NetMHCpan arm · RESOLVED

**Opened:** 2026-10-07, **before any NetMHCpan score existed** · **Reopens:** D034
**Anchor being superseded:** `b83a741b`

**Decision: reopen the frozen repository to add NetMHCpan 4.1 as a third §18
arm, because the obstacle D006 recorded turned out to be two separable
obstacles and only one of them was real.**

### What changed since D033

D033 recorded NetMHCpan as "not obtained — distribution is behind a per-user
academic licence form at the DTU host". That conflated two things:

| | Gated? |
|---|---|
| The **training data**, which is what D006's admission rule needs | **No.** Open paper supplementary material, no form |
| The **software**, which produces the scores | Yes — academic form, institutional e-mail |

`NetMHCpan_train.tar.gz` (87 MB, sha256 `06f2c9f2…`) is published at
`services.healthtech.dtu.dk/suppl/immunology/NAR_NetMHCpan_NetMHCIIpan/` and
states plainly that it is "the data set used for training of NetMHCpan-4.1". So
the contamination check was possible all along, and D033's framing was wrong in
the direction that made the work look more blocked than it was.

The project owner obtained the academic licence on 2026-10-07 10:50 UTC, which
supplied the other half.

### M7 outcome, measured before the software arrived

| | NetMHCpan 4.1 | MHCflurry 2.0.0 | MHCflurry 2.3.0 |
|---|---|---|---|
| training peptides | **12,081,588** | 605,189 | 666,025 |
| overlap, test positives | **9.22%** | 8.29% | 9.11% |
| overlap, test negatives | **3.32%** | 1.20% | 1.16% |
| positive : negative bias | **2.8 : 1** | 6.9 : 1 | 7.9 : 1 |

**Verdict: `OVERLAPPING`, quantified.** Admissible under D006 without invoking
the `UNVERIFIABLE` rule.

**One thing this arm does not inherit.** D006's asymmetry argument — that
contamination can only flatter a predictor, so a CNN win over a contaminated
predictor is conservative — rests on the overlap being lopsided toward
positives. At 2.8:1 it is markedly less lopsided than MHCflurry's ~7:1, because
NetMHCpan has also seen 3.32% of our negatives and may have learned that they
were not eluted. The one-direction reading is therefore **weaker for this arm**
and is not relied on; the mutually-naive row set (D033) remains the primary,
and it now excludes NetMHCpan's 12.5% as well, shrinking it below the current
175,524 rows.

### What reopening costs, stated plainly

`b83a741b` stops being the live anchor and `freeze.py --verify` will fail check
8 until the repository is re-frozen. **The superseded anchor remains valid for
what it covered** — the tree as it stood when §18 had two arms — and
`FREEZE_RECORD.md` will name it as superseded rather than delete it. A freeze
that can never be reopened is not a freeze, it is an embargo; a freeze that is
reopened silently is worthless. This entry is the difference.

**§25 is untouched.** The endpoint was read once and is closed. Nothing in this
arm can reopen it, and §18 remains secondary regardless of what NetMHCpan
scores — D014 bars a post-hoc switch whatever the numbers say.

### Protocol, fixed before the scores land

Identical to the MHCflurry arms: each peptide scored against its own
participant's recorded alleles, best allele taken, `Score_EL` as the comparable
quantity to MHCflurry's presentation score, `%Rank_EL` stored alongside so the
choice is reversible. Ambiguity-code rows excluded, so all three systems score
byte-identical rows. Reported on all three D033 row sets, with the
mutually-naive one primary.

**Installation verified against the vendor's own reference output:** the
package's `test/test.pep.out` reproduces exactly.

### Outcome, 2026-10-07

**NetMHCpan 4.1 scored 199,978 rows, every unit's count matching the number of
distinct peptides submitted.** On the common row set it reaches **0.5472**
against the CNN's 0.6852 — a gap of **+0.1380**, CI99 [+0.1068, +0.1634], 10 of
10 participants.

**The arm answered its own question in the negative.** D035 was opened partly
because a 12-million-peptide pan-allele predictor is a stiffer comparator than
MHCflurry's 0.67M and the CNN's lead had not been tested against one. It is now:
NetMHCpan 4.1 lands at 0.5472, MHCflurry 2.3.0 at 0.5479. **An eighteen-fold
larger training set buys nothing here**, and the lead is unchanged.

**One scoring run was discarded.** The first parse keyed each peptide's best
score on `Icore`, the interaction core after insertions and deletions, which
differs from the submitted peptide in 5.4% of rows and varies by allele. It
produced 2,292 keys from 2,000 benchmark peptides. The tell was a progress line
reading "24,462 peptides scored" for a unit holding 20,000 rows. Cost: 45
minutes. The script now keys on the submitted peptide, retains raw output per
unit so a parsing error never costs a re-run again, and asserts each unit's key
count against the peptides submitted.

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

A third followed: the manifest was written, then `FREEZE_RECORD.md` and this
entry were edited to describe the second fix, and the manifest was committed
carrying their pre-edit hashes. Check 8 would have caught it on a re-verify that
was not run. The fix is structural rather than procedural — `--write` now
re-reads and re-hashes the manifest it has just written and aborts if anything
in the tree has moved, so the window between writing and committing cannot be
filled with edits.

All three are recorded because a verification tool that has never produced a
failure has not been tested, and every failure this one has produced was its
own or the freeze's.

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
| NetMHCpan 4.1 | **Software** correctly described: a per-user academic licence form, which the project owner submitted on 2026-10-07. But this row conflated software with training data — **the training data was open all along**, so the M7 check was never blocked. Obtained and scored under D035 |
| MixMHCpred | ~~**not obtained** — distributed via `raw.githubusercontent.com`, which returns 404 through this proxy, unlike release assets~~ **THIS WAS FALSE.** That host returns 200 on any real file path; the bare host was probed and the result generalised. Obtained and scored under D036 |

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

## D041 — `REPORT.md` and `PROJECT_PROMPT.md` withheld pending submission · RESOLVED

**Opened:** 2026-10-11 · **Supersedes D039 in part** · **Requested by the
project owner**

**Decision: untrack `REPORT.md` and `PROJECT_PROMPT.md` from the published
tree, pending submission. The other six documents D039 restored stay shipped.**

D039 is not edited. It reversed D038 for eight documents on the reasoning that
withholding the report removed the study's only statement of its own limits.
That reasoning is answered rather than contradicted: `LIMITATIONS.md`, which
D039 itself created, now carries the limitations ledger unconditionally, so the
published tree keeps a full statement of what the numbers do not support even
with the report withheld. That was the point of extracting it.

### 1. What is withheld, and what carries its content

| document | reason | what carries it |
|---|---|---|
| `REPORT.md` | pending submission | `LIMITATIONS.md` (26 entries, status, what would close each); every headline number in `README.md`, `results/` and `freeze_manifest.json` |
| `PROJECT_PROMPT.md` | the internal brief the project was run from | `PREREGISTRATION.md` for what was specified, `METHODOLOGY.md` for what was done, this log for every departure |

`METHODOLOGY.md`, `SECTIONS.md`, `RUN_LOG.md`, `DECISION_LOG.md`,
`ENVIRONMENT.md` and `POWER_ANALYSIS.md` remain shipped. An earlier draft of
this change untracked all eight; it was narrowed to two at the owner's
instruction before anything was committed.

### 2. What it costs, stated plainly

- **`freeze.py --verify` no longer fully passes on a public clone.** Checks 3
  and 4 read the report. The other seven run, and they are the ones that bind
  the published tree. `README.md` and `.github/README.md` now say this.
- **Section 18's prose is not public**, though every number in it is:
  `results/predictors/*_test_scores.csv`, `results/qc/predictor_comparison_all.json`
  and `results/qc/contamination_all.json`. This matters for D040, where DTU's
  §7(v) consent was requested for publishing the benchmark — the published
  artefacts are unchanged by this entry, so D040's position is unchanged.
- **Untracking is not erasure.** Both documents remain in this repository's
  history and are recoverable by anyone who clones, exactly as D038 section 2
  recorded for the nine. Removing them from history is a separate decision with
  separate costs and is not taken here.

### 3. How the references were repaired

Both are entered in `DECLARED_ABSENT` in `scripts/check_references.py`, the
mechanism D039 built for exactly this: a reference to something deliberately
unshipped is declared with a reason and printed on every run, never silently
passed. The gate's validation purpose is unchanged — anything not declared
still fails it.

Prose that *instructed* a reader to consult the report was rewritten rather
than declared, because a declaration makes a citation honest, not a pointer
useful: `README.md` (status banner, the predictor-spread paragraph, the freeze
checks), `.github/README.md`, `LIMITATIONS.md` and `THIRD_PARTY_NOTICES.md` now
point at shipped artifacts. `FREEZE_RECORD.md` records a past freeze and is
annotated, not rewritten.

**RESOLVED.** The gate passes: 33 shipped documents scanned, every reference
resolves or is declared.

---

## D042 — `REPORT.md` and `PROJECT_PROMPT.md` removed from the whole history · RESOLVED as to the rewrite, PUBLICATION PENDING

**Opened:** 2026-10-11 · **Follows D041** · **Requested by the project owner**

**Decision: rewrite every commit so that neither document appears anywhere in
this repository's history, and republish from the rewritten history.**

D041 untracked both files from the published tree and said plainly what that
did not do: "untracking is not erasure. Both documents remain in this
repository's history and are recoverable by anyone who clones." The owner's
requirement is that they not be publicly accessible at all. That cannot be met
by any commit added on top, only by rewriting what is already there.

### 1. What was done

`git filter-repo --path REPORT.md --path PROJECT_PROMPT.md --invert-paths`,
run against a full backup taken first (`git bundle create --all`, 94 MB,
verified complete). Result: **0 commits and 0 objects** anywhere in the
repository now carry either path, across every ref.

Both files remain on local disk, gitignored, byte-identical to the copies in
the owner's private tree (SHA-256 verified before and after the rewrite).

### 2. What changed, and what is now void

- **103 commits became 98.** Five commits whose only content was `REPORT.md`
  became empty and were pruned: "Write the Introduction section", "Write the
  Methods section"'s sibling entries — specifically Introduction, Results,
  Discussion, Limitations and Conclusion. The work they describe survives in
  the sections' own records; only the commits that carried the report text are
  gone.
- **Every commit SHA from `943a806` onward changed.** Anchors quoted in this
  log and in `FREEZE_RECORD.md` no longer resolve. The mapping for the ones
  those records name:

| quoted as | now |
|---|---|
| `f7550f54` — the preregistration freeze anchor (D009) | `151b6999` |
| `21048535` — first re-freeze anchor | `5ac29a41` |
| `c26719d` — public-release preparation (D037) | `a33a079f` |
| `574b2f8` — the D038 untracking | `4f8efa09` |
| `4cef8eb` — the D039 reversal | `d1eccaa3` |
| `c41bd51` — the fourth re-freeze | `b9951105` |
| `e9ee11d` — the D041 withholding | `0d48ff7f` |

  Earlier entries are **not edited**, per this log's append-only convention.
  This table is the key for reading them.
- **`freeze_manifest.json` regenerated:** 373 entries to **371**. All nine
  checks pass, including the post-write re-hash.
- **Digests are not content.** `freeze_manifest.json` and `FREEZE_RECORD.md`
  still record each file's path and SHA-256 at the freezes that carried them.
  A SHA-256 is one-way; an 86 KB document cannot be reconstructed from it.
  Scrubbing those digests would mean rewriting a checksum-verified provenance
  chain to conceal a non-reversible hash, which was rejected as a worse trade.

### 3. Why the remote is deleted and recreated rather than force-pushed

A force-push would **not** have met the requirement. GitHub kept
`refs/pull/1/head` at `21048535`, a ref the repository owner cannot rewrite or
delete by pushing, and its tree contained both documents; the pull request's
own file view would have kept rendering them. Unreachable objects also stay
fetchable by SHA until GitHub garbage-collects, on no schedule the owner
controls.

Deleting the GitHub repository and recreating it destroys the pull-request refs
and every unreachable object outright. The cost was checked before choosing:
**0 forks, 0 stars, 0 watchers, 0 releases, no tags**, one closed pull request
and one issue. Lost: that pull request and issue, the 2026-10-06 creation date,
and any external link to an old SHA. Nothing cites this repository yet and no
DOI has been minted — D040 is holding that — so this is the cheapest point at
which the exchange could be made.

### 4. What this does not claim

Anyone who cloned or forked the repository before 2026-10-11 still holds both
documents, and no action here reaches them. The inspection recorded 0 forks and
0 watchers at the time of the rewrite, which bounds the exposure but does not
eliminate it. **No credential was ever committed** — the whole 103-commit
history was scanned for token, key and quoted-secret patterns and returned
nothing — so no rotation is required.

**RESOLVED as to the rewrite.** The republication step is the owner's and is
recorded here when it is done.

---

## D043 — S7 retrieved and read; two findings and one correction · RESOLVED

**Opened:** 2026-10-12 · **Closes the S7 gap D037 opened**

**Decision: retrieve and read the dataset publication, record the depositors'
identification pipeline verbatim, and correct one claim this report made about
it without having read it.**

S7 stood at `PENDING` for the whole working life of the project and at
IDENTIFIED-NOT-RETRIEVED after D037. The article was read in full from
PMC8297687. `DATA_SOURCES.md` S7 carries the parameters; this entry records
what they change.

### 1. Two findings that bound existing claims

**Class-I identifications were accepted at 5% FDR**, not 1% — "limited to 5%
for HLA class I- and 1% for HLA class II-presented peptides", by Percolator
2.04. Every peptide in the frozen positive class inherits that threshold.
Roughly one positive in twenty may be a misidentification. This is an upstream
source of label noise additional to the 11.78% decoy contamination, it was not
known when D004 concluded that confidence-based refiltering removes only 0.7%,
and it places a ceiling on achievable performance independent of any modelling
choice.

**The fragment mass tolerance differs by instrument** — 0.5 Da for ion-trap
spectra on the LTQ Orbitrap XL against 0.02 Da for orbitrap spectra on the
Orbitrap Fusion Lumos. **This is a mechanism for R5's platform separability**
(AUROC 0.6451 against a 0.5150 control). The platforms were not only acquired
differently, they were searched under different tolerances, so the identified
peptide populations can differ for reasons upstream of biology. R5 measured the
effect without being able to explain it; the explanation is now on the record,
and it is a documented processing choice rather than an opaque batch effect.

### 2. A circularity risk, raised and closed

The depositors state that "HLA class I annotation was performed using SYFPEITHI
1.0 and NetMHCpan 4.0". If that annotation had *filtered* which peptides entered
the deposited class-I set, benchmarking against NetMHCpan 4.1 in §18 would be
circular to an unknown degree.

**It did not.** The deposited containers are Proteome Discoverer `.msf`
databases holding the search output: their `Peptides` tables carry **8,361,615
rows across 51 units** before any length window, against the **58,554 unique
class-I ligands the article reports**. The deposited results are therefore the
full Percolator-passing identification set, and the article's figure is a
curated subset selected downstream for warehouse design. The NetMHCpan 4.0
annotation belongs to that downstream selection, not to the deposited data this
project extracted. §18 is not circular.

### 3. A correction

`REPORT.md` Methods states: "The deposited search was already restricted to
8–12 residues." **That is wrong.** The source article states no search-stage
length restriction — its only length constraint, 20 residues, applies to
warehouse peptide selection. The 8–12 window is applied by this project, in
`scripts/extract_peptides.py` (`LO, HI = 8, 12`, applied in the SQL that reads
each container), and is recorded per unit as `length_window` in
`data/derived/peptides/*.meta.json`.

The claim was made about a document that had not been read, which is precisely
the failure mode D037 flagged when it left S7 unretrieved. **No number changes:**
the window was applied either way and the frozen dataset is untouched. What
changes is the attribution of a design choice — from the depositors to this
project — and that belongs on the record.

`REPORT.md` is withheld under D041 and is not edited here; the correction is
recorded in this entry and carried into any manuscript drawn from it.

**RESOLVED.**

---
## D044 — Three construction defects measured; the preregistered result is unchanged and the margins are restated · RESOLVED as to measurement

> **Pointer, added 2026-10-12 by D058:** defect B's **[ESTIMATE]** of −0.0030 AP
> is **confirmed, not replaced**. D058 reproduces it at −0.0031 as the realistic
> insertion case, shows the unique-versus-occurrence ambiguity this entry
> flagged is worth 0.0009% of the negative pool, and adds an assumption-free
> worst case of **−0.0301** that the preregistered decision survives. One
> discrepancy against this entry's eligible-pool figures is **unresolved**. This
> entry is not otherwise edited.

**Opened:** 2026-10-12 · **Follows D043** · **Requested by the project owner**

**Decision: record three defects with their measured effect, modify no frozen
artifact, leave the preregistered threshold at 0.647, and report corrected
figures alongside the preregistered ones rather than in place of them.**

An independent re-derivation was run against the frozen artifacts, sharing no
code with this repository. It reproduced the primary endpoint **from the 25
frozen checkpoints** at 0.7550853623 against the recorded 0.7550853665 — a
difference of **-4.2e-09** — and reproduced the leakage percentage, the four
predictor average precisions and their 0.0046 span. **The study's results
stand.** Three construction defects were found in the course of it.

Throughout this entry, three kinds of statement are kept apart and labelled:

- **[FACT]** — read directly from a frozen artifact or from code, or computed
  exactly from them.
- **[ESTIMATE]** — a quantity derived under a stated modelling assumption.
- **[SENSITIVITY]** — the result of a simulation that perturbs the frozen data
  and re-evaluates. Not a measurement of the study as conducted.

---

### 1. Defect A — the composition floor is measured on a different population from the endpoint it gates

**[FACT]** `scripts/negative_diagnostic.py` draws its positives as
`rng.sample(sorted(observed), 60000)`: 60,000 peptides taken uniformly at random
from the 2,658,972-peptide observed union, with no reference to participants. It
generates its own negatives rather than reading `NEGATIVES.csv`, and evaluates
on a random 50/50 split of that sample. The recorded result is AUROC 0.6085,
corresponding to **AP 0.597**, which D008 used as the floor.

**[FACT]** The endpoint is measured on a different population: the frozen
dataset of 10,000 positives per participant, stratified by that participant's
own length distribution, evaluated per unit on ten held-out participants.

**[FACT]** The composition-only floor recomputed on the population the endpoint
actually uses:

| protocol | population | AUROC | AP |
|---|---|---|---|
| random 50/50 row split | frozen dataset | 0.6460 | 0.6378 |
| participant-held-out | frozen dataset | 0.6483 | 0.6367 |
| **mean per-unit AP** (the endpoint's estimand) | frozen dataset, 10 test units | — | **0.6360** |
| as recorded in D002/D008 | 60k uniform sample of the union | 0.6085 | **0.5970** |

**[FACT]** The evaluation protocol is not the cause: a random 50/50 split gives
0.6378 and a participant-held-out split 0.6367 on the same data. The population
is the cause. 79.9% of the union occurs in exactly one participant, so uniform
sampling over-weights rare peptides, while per-participant capped sampling
over-weights abundant and recurrent ones, which separate more easily on
composition alone.

**[FACT]** The re-derived floor is itself an estimate over 10 units and carries
a cluster-bootstrap nominal-99% interval of **[0.6057, 0.6673]**. A
floor-plus-0.05 threshold built from it is therefore **0.6860 point, CI99
[0.6557, 0.7173]** — an interval, not a number.

**The preregistered threshold of 0.647 is NOT changed by this entry.** Revising
a threshold after seeing the result it gates is precisely what preregistration
exists to prevent. 0.647 remains the rule of record; 0.6860 is reported beside
it as a sensitivity, with its own interval.

### 2. Defect B — the decoy pool is not blind to the test partition

**[FACT]** `build_dataset.py` accumulates `observed` across all 52
participants, the ten held-out included, and rejects any candidate decoy found
in it. Its own assertion records the outcome:
`("no negative is observed", not (allneg & observed))`. A candidate decoy
presented by a *test* participant is therefore removed using information that
would not exist prospectively.

**[FACT]** 364,900 peptides — 13.72% of the universe — are observed only in
test units; 361,740 of them occur in the reference proteome as 8-12-mers. The
proteome was re-retrieved for this audit and its SHA-256 matches S5's recorded
value exactly, so the k-mer space is reconstructed from the same bytes. This
also independently confirms S5's provenance record.

**[FACT]** Eligible pool and test-only overlap, per length:

| L | unique k-mers in expressed proteins | eligible pool as built | test-only, in proteome | negatives drawn |
|---|---|---|---|---|
| 8 | 10,313,958 | 9,905,950 | 56,568 | 81,422 |
| 9 | 10,418,712 | 9,685,563 | 101,711 | 160,700 |
| 10 | 10,479,904 | 9,783,092 | 97,071 | 132,243 |
| 11 | 10,523,245 | 10,031,599 | 67,375 | 89,813 |
| 12 | 10,554,716 | 10,249,119 | 39,015 | 55,822 |

**[ESTIMATE]** Assuming the reservoir draws approximately uniformly from the
unique eligible pool, a test-blind construction would have admitted
**4,242.5 false negatives of 520,000 (0.816%)**, of which **815.9 fall in the
test partition — 81.6 per test unit**. The assumption is imperfect:
`build_dataset.py` reservoir-samples k-mer *occurrences* and then deduplicates,
slightly over-representing sequences that occur in several proteins. Direction
of that bias is not established; magnitude is expected to be small relative to
0.816%.

### 3. Defect C — ambiguity codes are perfectly label-correlated

**[FACT]** Negatives are filtered to standard residues
(`not set(c) <= AA`); positives are not. Any peptide containing X, B or Z is
therefore deducibly positive: **181 positive rows (0.035%), 0 negative rows, 22
rows inside the test partition (0.011%)**. The encoder compounds this by mapping
an unknown character to the pad token.

**[SENSITIVITY]** Removing all 22 ambiguity rows from the test partition moves
the primary endpoint from 0.7550854 to 0.7550806: **-4.81e-06**, largest
per-unit change 4.69e-05. **No reported decimal changes.** Recorded because the
two classes were drawn from different alphabets, which is a construction defect
whatever its magnitude.

### 4. Statistical procedure, and the margins

**[FACT]** Method of record, unchanged: the estimand is the mean per-participant
average precision; uncertainty is a cluster bootstrap over the 10 test
participants, B = 10,000, percentile interval at 0.5/99.5 (nominal 99%, chosen
because R6 measured nominal 95% to deliver only 0.884-0.890 actual coverage).
D008 rejects the null when the nominal-99% lower bound exceeds 0.647.

**[SENSITIVITY]** The counterfactual for defect B was simulated holding row
count and prevalence fixed: for each test unit, 82 randomly chosen negatives
were replaced by rows carrying the 25-model score vectors of that unit's own
leakage-free positives — peptides the model never saw in training — relabelled
0. Ten independent replicates; each re-bootstrapped from its own per-unit
values.

**[FACT/SENSITIVITY]** Lower bounds and margins. Every bound below is a fresh
cluster bootstrap on the relevant per-unit values; none is obtained by shifting
another bound.

| partition | treatment | mean AP | CI99 lower |
|---|---|---|---|
| primary | as frozen | 0.755085 | 0.7372 |
| primary | counterfactual, k = 82/unit | 0.752213 (sd 0.00028) | 0.7343 (sd 0.0003) |
| leakage-free | as frozen | 0.705579 | 0.6923 |
| leakage-free | counterfactual, k = 82/unit | 0.702253 (sd 0.00028) | 0.6894 (sd 0.0003, min 0.6889) |

Margins against three thresholds — the preregistered one, the re-derived point
estimate, and the upper end of the re-derived threshold's own interval:

| partition | treatment | vs 0.647 (preregistered) | vs 0.6860 (re-derived point) | vs 0.7173 (re-derived CI99 upper) |
|---|---|---|---|---|
| primary | as frozen | **+0.0902** | **+0.0512** | **+0.0199** |
| primary | counterfactual | **+0.0873** | **+0.0483** | **+0.0169** |
| leakage-free | as frozen | **+0.0454** | **+0.0064** | **-0.0249** |
| leakage-free | counterfactual | **+0.0424** | **+0.0034** | **-0.0279** |

**What this supports, stated precisely:**

- **Against the preregistered threshold of 0.647, every test rejects**, on both
  partitions, with and without the defect-B counterfactual. The preregistered
  claim is intact.
- **Against the re-derived floor's point estimate**, every test still rejects,
  but the leakage-free margin is **+0.0064 as frozen and +0.0034 under the
  counterfactual**.
- **Against the upper end of the re-derived threshold's interval**, the primary
  endpoint still rejects (+0.0169) while **the leakage-free sensitivity does
  not** (-0.0279). This is a deliberately conservative treatment — carrying a
  nuisance parameter at its interval's unfavourable end is not a standard
  procedure — but it bounds the claim and is recorded rather than omitted.

**The honest summary of the unpaired analysis:** the primary endpoint survives
every treatment. The leakage-free sensitivity survives the preregistered rule
comfortably and the re-derived floor narrowly, and fails only under the most
conservative handling of the floor's own uncertainty.

#### 4a. The paired analysis, which supersedes the fragility above

**[FACT]** The floor and the endpoint are estimated on **the same ten units**,
so comparing a bootstrap bound on one against a point estimate of the other
treats two dependent quantities as independent and discards the pairing. The
correct statistic for "does the model beat composition by at least 0.05" is the
**per-unit difference**, bootstrapped over units.

**[FACT]** Doing so also exposes a second population mismatch in the unpaired
comparison above: the leakage-free CNN endpoint was being compared against a
floor measured on the **full** test partition. The composition classifier scores
differently on the leakage-free subset, and the matched floor there is 0.5830,
not 0.6360.

| partition | CNN mean | composition mean | **paired difference** | paired CI99 | units with diff > 0.05 | smallest unit |
|---|---|---|---|---|---|---|
| primary | 0.7551 | 0.6360 | **0.1191** | [0.0988, 0.1394] | **10 / 10** | 0.0844 |
| leakage-free | 0.7056 | 0.5830 | **0.1226** | [0.1005, 0.1446] | **10 / 10** | 0.0842 |

**[FACT]** Against the preregistered lift of 0.05, the paired lower bound clears
by **+0.0488** on the primary partition and **+0.0505** on the leakage-free
subset. Every one of the ten held-out participants shows a difference above
0.05, the smallest being 0.0842.

**Why this matters.** The wide floor interval — CI99 [0.6057, 0.6673] — is
dominated by between-unit variance: units that are easy for the CNN are easy for
the composition classifier. Pairing cancels that shared variance, and the paired
interval is correspondingly tight. **The apparent fragility of the leakage-free
margin (+0.0034) is an artefact of the unpaired comparison and of the
population mismatch, not a property of the result.** On the matched, paired
analysis the conclusion is not marginal on any partition.

The paired statistic is **not** what D008 preregistered, and does not replace
it. It is reported as the statistically appropriate sensitivity, and it
strengthens rather than weakens the preregistered finding.

### 5. What this entry does NOT do

- **No frozen artifact is modified and no result is restated.** The dataset,
  split and endpoint remain byte-identical to what `PREREGISTRATION.md`
  committed to. `freeze_manifest.json` is untouched by this entry.
- **The preregistered threshold stays 0.647.**
- **The defect-B sensitivity is not the counterfactual.** The complete
  counterfactual would regenerate the negative pool excluding only
  training-unit peptides, rebuild the frozen dataset, re-run model selection and
  refit all 25 models. That changes *training* data as well as test data, and
  was not done. What was measured is the test-side effect only, with the
  training set held at what it actually was. A full rebuild could move the
  result in either direction and is the only way to settle defect B.
- **Only the primary and leakage-free endpoints were re-evaluated.** Every
  secondary analysis — cross-platform transfer, allele-exclusive, multi-allele
  — inherits the same decoy construction and was not re-examined.

### 6. Correction to an earlier draft of this entry

An earlier draft of this entry reported a leakage-free margin of "+0.0036" obtained by taking the
recorded CI99 lower bound and adding a point-estimate delta. **That is not a
valid interval operation** and the figure is withdrawn. The bound must be
recomputed by bootstrapping the perturbed per-unit values, which gives **+0.0034
against the re-derived point threshold** — numerically close, but arrived at
correctly, and accompanied here by the interval on the threshold itself, which
that draft omitted entirely.

**RESOLVED as to measurement.** Three defects are quantified. None reverses a
conclusion under the preregistered rule. Carrying the corrected figures and the
floor's interval into any publication is required, and `LIMITATIONS.md` should
gain an entry for each defect.

---

## D045 — Two further withheld documents remain in the published history, by decision · RESOLVED

**Opened:** 2026-10-12 · **Scopes D042** · **Requested by the project owner**

**Decision: accept that `HANDOVER.md` and `PXD024871_CNN_Experiment_Proposal.md`
remain recoverable from this repository's public history, and record that
rather than leave the record implying otherwise.**

D042 rewrote the history to remove `REPORT.md` and `PROJECT_PROMPT.md` from
every commit, and they are gone: **0 commits and 0 objects** carry either path.
That rewrite was scoped to those two files alone. The other two withheld
documents were not touched and are still present in commits that are ancestors
of `origin/main`:

| document | content-bearing commit | public fetch, verified 2026-10-12 |
|---|---|---|
| `HANDOVER.md` | `24a99dd` | HTTP 200 |
| `PXD024871_CNN_Experiment_Proposal.md` | `8537ba9` | HTTP 200 |

Both were verified by fetching them from `raw.githubusercontent.com`. Note that
the *removal* commits — `4f8efa0` and `a33a079` — return 404, because the files
are absent from those trees; the content lives in the parent commits, and a
check against the removal commit alone would wrongly report the material as
gone.

### Why this is accepted rather than fixed

- **Neither document carries a credential.** `HANDOVER.md` records the project's
  cloud spend and an instruction to create a GitHub token with `repo` scope as a
  Colab secret. It states a scope, never a value. A scan of the entire history
  for token, key and quoted-secret patterns returned nothing. **No rotation is
  required.**
- **Neither carries personal or patient data.** The experiment proposal is an
  internal T-A4 planning document withheld under D037 for being unpreregistered,
  not for being sensitive.
- **A second rewrite would void D042's own mapping table.** That table is the
  key by which every earlier entry in this log is read. Rewriting again would
  invalidate the new SHAs as well, require deleting and recreating the GitHub
  repository a second time, and buy little against material that carries no
  secret.

### What this entry fixes

D038 §2 and D041 both state in general terms that untracking does not remove a
file from history. Neither names which documents are actually still there. This
entry names them, with the commits and the verification, so that a reader
checking the claim finds an accurate answer rather than an implication that all
withheld material was purged.

**RESOLVED.** Revisit only if a future decision requires these two to be
unrecoverable, in which case the procedure is D042's, applied to these paths.

---


## D046 — The workflow signature replicates in an independent cohort; the instrument-specific claim does not · RESOLVED

> **Pointer, added 2026-10-12 by D054, completed by D055:** the code and
> provenance behind this entry are in the repository
> (`scripts/extract_px4023.py`, `scripts/replicate_px4023.py`,
> `data/external/PXD004023/`, run-011). **The figures below are superseded.**
> They were one draw from a hash-ordered procedure, not a reproducible value.
> **D055 replaces them with 0.6604 held-out AUROC, 0.6135 control and an excess
> of +0.0469, nominal-99% [+0.0194, +0.0699]**, deterministic across hash seeds
> and recorded in `results/replication/px4023.json`. The direction and the
> 6-of-6 donor count hold. This entry is not otherwise edited.

**Opened:** 2026-10-12 · **Follows D044** · **Requested by the project owner**

**Decision: test the composition-only platform finding on an independent public
dataset, report what replicates and what does not, and change no PXD024871
result.**

R5 measured the acquisition platform to be separable from peptide composition
alone at AUROC 0.6451 against a 0.5150 control. D044 confirmed that figure on
re-derivation. It rested on one submission, and no published work was found that
reports the same phenomenon, so it had no external support.

### 1. What was tested, and why it is not an instrument replication

**PXD004023** (Pearson et al., *J Clin Invest* 2016, PMID 27841757): HLA class-I
immunopeptidomes of B-lymphoblastoid cell lines from 18 volunteers, Thibault
laboratory, IRIC Montreal. An independent cohort, laboratory and instrument
pair.

PRIDE reports a submission's `instruments` field as a **union across the
submission**, not per file, so it cannot label a run. All 160 raw files were
therefore labelled from their own headers, by HTTP range request over bytes
0-1048576 — 161 MB against a 97 GB raw dataset. **Every run resolved; none was
ambiguous or conflicting:**

| Era | Runs | Instrument | Fractionation |
|---|---|---|---|
| December 2013 | 95 | Orbitrap Elite | SCX, 5 fractions — 95 of 95 |
| May-October 2014 | 65 | Q Exactive Plus | none — 0 of 65 |

**No run breaks the pattern.** Instrument, acquisition year and fractionation
are perfectly collinear in this cohort and cannot be separated. The analysis is
therefore a test of the acquisition **workflow**, not of the instrument, and
that distinction is load-bearing: **SCX fractionates by charge, a direct
function of amino-acid composition**, which is the classifier's feature space.
Fractionation alone could produce a positive result.

### 2. Design

Six donors — C, CELG, J, MA, PF1, RT — have data on both workflows, giving a
paired within-donor design that PXD024871 cannot provide, since no participant
there spans both platforms. All material is B-LCL, so material type is constant.

**The evaluation unit is the donor.** Runs and SCX fractions are technical
subdivisions of one sample; treating them as replicates would be
pseudoreplication.

The frozen procedure of `scripts/leakage_audit.py` is preserved: 20-dimensional
amino-acid composition, no positional information, Fisher linear discriminant,
AUROC with midrank ties, class balance by subsampling. The classifier is
refitted on the new cohort — that is the method, not a deviation, since it was
never a portable fitted model. **Evaluation is strengthened** to
leave-one-donor-out, where the original split peptides 50/50 and permitted a
donor to appear on both sides.

### 3. Result

| Donor | Elite | Q Exactive Plus | Held-out AUROC |
|---|---|---|---|
| C | 7,188 | 5,987 | 0.6630 |
| CELG | 9,737 | 5,798 | 0.6422 |
| J | 8,511 | 6,810 | 0.6192 |
| MA | 5,839 | 4,785 | 0.6766 |
| PF1 | 8,056 | 6,248 | 0.6715 |
| RT | 3,910 | 4,411 | 0.6856 |
| **mean** | | | **0.6597** (sd 0.0247) |

Control, random halves of donors as in the frozen procedure: **0.5998**.
**Excess over control: +0.0598.** Without the 8-12 window: 0.6582 against
0.6039, excess +0.0544. Separable in **6 of 6 donors**.

**The excess, not the raw AUROC, is the comparable quantity.** Donors are more
separable in this cohort (control 0.5998) than in ours (0.5150), so +0.0598
against +0.1301 is the honest comparison, not 0.6597 against 0.6451.

A length mechanism recurs: 9-mers are 50.8% of the unfractionated set against
38.6% of the fractionated one; 12-mers 1.8% against 4.4%.

### 4. What this does and does not establish

**Establishes:** a composition-only classifier separates acquisition workflows
in a second cohort, a second laboratory and a different instrument pair. The
phenomenon is not a property of one submission, which is what R5 could not show.

**Does not establish:** any instrument-specific claim. **R5's finding is not
replicated** — it is adjacent. In PXD024871 platform was confounded with
participant but *not* with sample preparation; here it is confounded with both
year and fractionation. The two results support the same practical warning and
different mechanisms.

**What would settle it:** a cohort in which the same samples are acquired on
different instruments under one preparation protocol. No public dataset is known
to provide this, and the search that found PXD004023 did not surface one.

### 5. A provenance finding worth keeping

One identification file, `CELG_rep3_021213.mzid`, arrived at **exactly the
manifest byte count** while containing `<Error><Code>ConnectionClosedException</Code>`
injected into its body mid-stream. **Size agreement did not detect it; only XML
parsing did.** An earlier run of this analysis used the truncated file and its
figures were discarded; the numbers above are from the re-fetched file, after
all 37 files were verified well-formed.

This is the same failure mode `scripts/extract_peptides.py` already guards
against by refusing any container whose publisher checksum is unverified, and it
is evidence that the guard earns its cost. **A size check is not an integrity
check.**

### 6. Scope

No PXD024871 artifact, result, figure, manifest or preregistered rule is changed
by this entry. The replication is recorded in the manuscript draft and in
Supplementary Methods S6, both of which are private and unpublished. Data
retrieved: 161 MB of headers and 1.13 GB of identification results, against a
3 GB ceiling agreed in advance.

**RESOLVED.** The workflow claim has independent support. The instrument claim
remains single-cohort and is reported as such.

---


## D047 — A size check is not an integrity check; the exposure at S2 · RESOLVED

**Opened:** 2026-10-12 · **Follows D046 section 5** · **Requested by the project owner**

**Decision: record where this project's own retrieval path is exposed to
size-preserving corruption, state what currently protects it, and say plainly
what that protection does and does not establish.**

D046 section 5 records the incident that prompted this: a file arriving at its
declared byte count with an error payload inside it. That narrative is not
repeated here. This entry concerns the distinct question of **where the same
failure mode could reach this project's own data**, and it makes no claim that
any file here is corrupted or that any reported result is wrong.

### 1. The exposed source

Retrieval here is checksum-verified wherever a publisher checksum exists.
`scripts/extract_peptides.py` refuses any container whose provenance record does
not show `published_checksum_verified` as true, and that guard caught a real
truncation during the extraction run — a transfer that stopped at 77%
(`REPORT.md` Methods).

**One source has no publisher checksum.** S2, the community-annotated sample
metadata file, records `"published_checksum": "ABSENT"` in
`data/raw/S2/provenance.jsonl`. It is also the most load-bearing single file in
the project: the only evidence for sample class, participant identity and
genotype, with M1, M2, M3 and M4 all resolving through it.

### 2. What currently stands in for publisher verification, and what each
establishes

**Our own SHA-256**, `cdda54ce…f2a85`, recomputed for this entry and matching the
provenance record exactly. **What it establishes:** the file on disk is
byte-identical to what was received on 2026-10-06, so nothing has altered it
since. **What it does not:** that the bytes received faithfully reproduce the
publisher's file. A hash computed after download fingerprints the transfer's
output, whatever that output was; a corrupted transfer hashes consistently and
stably.

**Agreement with the manifest's declared 317,806 bytes**, verified on disk and
asserted as a check in `scripts/phase_a_mapping.py` line 175. **What it does
not establish:** anything about corruption that preserves file length. That is
exactly the class of failure D046 observed.

**Structural validation and the bidirectional join.** The file parses as 402
data rows, and M1 matched 402 acquisitions against 402 metadata rows in both
directions with zero manifest-only and zero metadata-only rejects
(`results/qc/QC_G1.md`). **What this establishes:** several classes of
corruption — truncation, injected payloads, row loss — would break the row
count or the join, and did not. **What it does not establish:** authenticity or
semantic correctness. A file could be internally consistent, join perfectly, and
still differ from what the depositors published.

**Taken together these are partial protection. They are not equivalent to
verification against a trusted publisher digest**, and the distinction is worth
holding because the project's own documentation of S2 emphasises the SHA-256,
which is the weakest of the three for this purpose.

### 3. A correction found while verifying this entry

A draft of this entry stated that S2 carries 37 columns, following `REPORT.md`
Methods, which says "402 rows, 37 columns". **The file on disk has 39
tab-separated header fields.** The row count of 402 is correct; the column count
is not. No analysis in this project selects columns by count or position — M1
through M4 address fields by name — so no result depends on the figure, and
nothing is recomputed.

`REPORT.md` is withheld under D041 and is not edited by this entry. The error is
recorded here so that the figure is not carried forward again; it had already
propagated into one unpublished manuscript draft.

This is also a small illustration of the entry's own point: a number that no
check tests can stay wrong indefinitely. `freeze.py` check 4 verifies headline
numbers in `REPORT.md` against their artifacts, and a column count is not among
them.

### 4. Scope

**No artifact, result, script or number is changed by this entry.** S2 is
byte-identical to its retrieval and remains so. The frozen dataset, split and
endpoint are untouched. This records a provenance risk and the safeguards that
currently cover it.

### 5. For anyone reusing this repository or its methods

Where a publisher checksum exists, verify against it. Where none exists, record
that absence in the provenance entry — as S2 does — and rely on structural
validation of the content rather than on the byte count, while recognising that
structural validation bounds corruption rather than proving fidelity.
Re-downloading a file and finding the same length establishes very little;
parsing it establishes a good deal more; neither replaces a trusted digest.

**RESOLVED.** The failure mode is recorded, the one exposed source is named, the
protections are stated with their limits, and one propagated factual error is
corrected.


## D048 — The NetMHCpan 4.1 withdrawal is precomputed, and the wait is given dates · RESOLVED as to preparation

> **Pointer, added 2026-10-12 by D051:** DTU Health Tech granted consent on
> 2026-10-12, so the withdrawal this entry prepared is **not executed**. The
> computation stays on the record: it is what established, before the answer
> arrived, that the licensing decision carried no scientific cost. The two
> decision dates it set — 2026-10-25 and 2026-11-08 — are cancelled.

> **Pointer, added 2026-10-12 by D050:** the two row counts and the two
> prevalences in the withdrawal table below are each 20 rows high, and the
> upper CNN lead is given as +0.1419 where the artifact gives +0.1418. Every
> average precision in that table is correct and reproduces exactly. D050
> carries the corrected table; the conclusion of this entry is unchanged.

**Opened:** 2026-10-12 · **Addendum to D040**, which is not edited beyond its
status pointer, per this log's append-only convention · **Requested by the
project owner**

**Decision: compute the withdrawal arm before the answer arrives, so that the
licensing decision costs a text edit rather than an analysis, and replace an
open-ended wait with two dated decision points.**

D040 asked DTU Health Tech for §7(v) consent on 2026-10-11 and specified what
happens on each answer. It left one gap: on refusal or silence, the withdrawal
was described but never computed, so the cost of that outcome was unknown while
the decision was pending. **A decision whose cost is unmeasured is not really
prepared for.**

### 1. The withdrawal, computed

Removing NetMHCpan 4.1 removes its overlap constraint, so the comparator
population **grows**. The honest withdrawal recomputes the common naive row set
over the three systems actually compared, rather than reporting three
predictors on a row set defined by a fourth that is no longer cited.

| | As published, 4 predictors | Withdrawal, 3 predictors |
|---|---|---|
| Common naive rows | 165,594 | **170,074** |
| Prevalence | 0.4397 | 0.4386 |
| CNN | 0.6852 | **0.6846** |
| MHCflurry 2.3.0 | 0.5479 | 0.5476 |
| MHCflurry 2.0.0 | 0.5443 | 0.5439 |
| MixMHCpred 3.0 | 0.5434 | 0.5429 |
| **Predictor span** | **0.0046** | **0.0047** |
| CNN lead | +0.1373 to +0.1419 | +0.1370 to +0.1417 |

**The finding survives, marginally strengthened.** Three groups, three training
corpora, three architectures still agree to within half a percentage point while
differing from the CNN together. No figure moves by more than 0.0006.

**The licensing decision therefore carries no scientific cost.** That is worth
knowing in advance: it means the answer can be accepted whatever it is, and
neither waiting nor withdrawing distorts what the study reports.

These numbers are recomputed from the frozen artifacts — `SPLIT.csv`,
`POSITIVES.csv`, `NEGATIVES.csv`, the four `TEST_PREDICTOR_OVERLAP_*.csv` and
the four `*_test_scores.csv` — using the 25 frozen checkpoints for the CNN arm,
under D027's mean-across-models rule. **Nothing is written into any artifact by
this entry**; `predictor_comparison_all.json`, `contamination_all.json`,
`comparison_with_predictors_all.csv` and F13 are untouched, and the published
§18 still reports four predictors.

### 2. Two dates, so silence is not a decision by default

D040 states that on no reply, "L26 stays open with the request on the record.
Not silently closed by the passage of time." That is right about what must not
happen and silent about when to act. Two dates fix it:

| Date | Action |
|---|---|
| **2026-10-25** | First follow-up to `health-software@dtu.dk`, two weeks after the request. Reference the 2026-10-07 licence grant and the 2026-10-11 request so DTU can locate both |
| **2026-11-08** | If still no reply, **treat silence as a non-answer and execute the withdrawal** using the numbers above. Record the outcome as a new entry, re-freeze, and proceed to submission and the DOI |

Four weeks total. The deadline is not a claim about what DTU owes; it is a limit
on how long this project will hold a result hostage to an unanswered email.

### 3. What does not change

The DOI still waits. A Zenodo deposit is immutable, and archiving before the
§18 arm is settled would permanently publish a tree that may then have to lose
one. That constraint is D040's and stands unaltered.

L26 in `LIMITATIONS.md` stays open until the answer arrives or 2026-11-08
passes.

**RESOLVED as to preparation.** The outcome remains external. What has changed
is that both branches are now costed, and the wait has an end.

---


## D049 — Two manuscript figures enter the tree, and check 5 stops counting · RESOLVED

**Opened:** 2026-10-12 · **Requested by the project owner**

**Decision: add the two figures the manuscript needs as `F14` and `F15`,
generate them from `scripts/make_figures.py` like every other figure, and
replace check 5's figure count with a named expected set.**

### 1. Why the numbering starts at F14, not F1

An earlier manuscript draft asserted that `F1`–`F6` "were planned in the project
specification and never produced". **That is wrong.** `F1` through `F7` are the
run-001 design findings set out in `POWER_ANALYSIS.md` — "F1 — The §25
hypothesis as written is close to unfalsifiable", "F6 — Class ratio drives
relative precision", and so on — and `SECTIONS.md` cites "run-001's F4 and F6"
on that understanding.

The `F` identifier space is shared between findings and figure files. The figure
files begin at `F7` for that reason, not because of a gap. Naming the new assets
`F1` and `F2` would have collided with six findings the reports already cite, so
they continue the series at **`F14`** and **`F15`**. The manuscript wording is
corrected; `POWER_ANALYSIS.md` and `SECTIONS.md` are untouched.

### 2. The figures

`F14_study_design.svg` — the design from deposited submission to the single
endpoint read, with everything fixed in advance on one side of a dashed line.
`F15_four_confounds.svg` — the composition floor, the leakage range over 2,000
splits, platform separability against its control, and decoy contamination, in
one panel.

Both are generated by `scripts/make_figures.py` from the frozen artifacts:
`FREEZE.json`, `SPLIT.csv`, `FILE_MAP.csv`, `POSITIVES.csv`,
`selection.json`, `final.json`, `endpoint.json`, `leakage_audit.json`,
`negative_diagnostic.json` and `predictor_task_mismatch.json`. **No scientific
value is typed into either figure**, so neither can drift from the tree it
depicts, and both regenerate byte-identically.

They use the existing CSS block and class set unchanged. Anything the shared
classes do not cover is an inline attribute referencing an existing custom
property, so **the seven earlier figures are byte-unchanged by their presence** —
verified by hashing all seven before and after.

### 3. The gate change, and why it is a strengthening

Check 5 previously asserted `len(before) == 7`. That is a count, and a count
cannot tell a rename from a replacement: swapping one figure for another of the
same name, or renaming a figure and adding a different one, would both pass.

It now compares against a **named expected set** of all nine filenames and fails
on any of three conditions — a missing figure, an unexpected extra figure, or
byte drift in any of them — and names which in the failure message.

**The gate is strictly stronger than before.** Verified by perturbation: a
single comment appended to `F7_endpoint.svg` produced

```
FAIL  9 figures reproduce from the artifacts  missing [] extra [] DRIFT ['F7_endpoint.svg']
```

where the previous form would have reported only that something drifted. The
reproducibility guarantee is unchanged in kind and tightened in scope: every
figure in the published tree is still regenerated from artifacts and compared
byte for byte on every freeze, and now the *set* is pinned as well as the bytes.

### 4. Scope

**No scientific result, frozen procedure or analysis changes.** The dataset,
split, endpoint, preregistered rule and every reported number are untouched.
`POWER_ANALYSIS.md` and `SECTIONS.md` keep their `F1`–`F7` findings unaltered.
The manuscript that uses these figures remains private and unpublished.

**RESOLVED.**

---


## D050 — A transcribed row count, corrected in three places · RESOLVED

**Opened:** 2026-10-12 · **Corrects D036 and D048**, neither edited beyond its
status pointer, per this log's append-only convention · **Requested by the
project owner**

**Decision: correct the common-row-set count wherever the repository states it,
make `F14` read that count from the artifact instead of carrying it as a
literal, and record that no average precision, interval or conclusion moves.**

### 1. The error

`results/qc/predictor_comparison_all.json` gives the row set naive to the CNN
and to all four predictors as **165,574 rows at prevalence 0.439628**. Three
places in the repository stated **165,594** instead, and one stated a
withdrawal count of 170,074 against a true 170,054.

The gap is **20 rows in every case**, and it has one cause. The test partition
holds 22 rows whose sequences carry ambiguity codes — X, B or Z — which
`results/predictors/ambiguity_skipped.csv` lists and which no predictor scored;
the scored files hold 199,978 rows, which is 200,000 less those 22. **Two of
those 22 sequences also occur in the model-selection partition**, so they are
removed by the naivety filter regardless. The remaining **20** are the entire
discrepancy, in all four of D036's row sets and in both of D048's columns.

D036's table was written while MixMHCpred 3.0 was still unscored — the entry
says so — so its counts were projected from the overlap lists, before the
exclusion existed in any scored file. D048 then took its first column from that
table rather than from the artifact.

### 2. The corrected counts

Recomputed from `SPLIT.csv`, `POSITIVES.csv`, `NEGATIVES.csv`, the four
`TEST_PREDICTOR_OVERLAP_*.csv` and the four `*_test_scores.csv`, by the row-set
construction in `scripts/compare_predictors_all.py`, unmodified:

| Row set (D036 §"The row-set problem this creates") | stated | correct |
|---|---|---|
| CNN + both MHCflurry | 175,544 | **175,524** |
| + NetMHCpan 4.1 | 170,648 | **170,628** |
| + MixMHCpred 3.0 | 165,594 | **165,574** |
| + NetMHCpan 4.2 | 141,276 | **141,256** |

Prevalence is unchanged at three decimals in all four — 0.440, 0.441, 0.440,
0.443 — and D036's argument rests on the deletion that admitting 4.2 would
cause, which is 29,372 rows either way. **No decision in D036 changes.**

### 3. D048's table, corrected

| | As published, 4 predictors | Withdrawal, 3 predictors |
|---|---|---|
| Common naive rows | **165,574** | **170,054** |
| Prevalence | **0.4396** | **0.4385** |
| CNN | 0.6852 | 0.6846 |
| MHCflurry 2.3.0 | 0.5479 | 0.5476 |
| MHCflurry 2.0.0 | 0.5443 | 0.5439 |
| MixMHCpred 3.0 | 0.5434 | 0.5429 |
| **Predictor span** | **0.0046** | **0.0047** |
| CNN lead | **+0.1373 to +0.1418** | +0.1370 to +0.1417 |

**Every average precision in D048 was already correct.** The recomputation
reproduces the frozen artifact exactly: the same 165,574 rows, the same
prevalence to six decimals, the same four predictor intervals bit-for-bit, and
a CNN mean of 0.6851994691 against the artifact's 0.6851994669 — a difference
of 2.2e-09, which is floating-point accumulation order across the 25
checkpoints, not a change in the quantity. Only the row counts, the two
prevalences and one interval endpoint were wrong, and only in the log.

**D048's conclusion stands unaltered**: the predictor span moves 0.0046 to
0.0047, no figure moves by more than 0.0006, and the licensing decision still
carries no scientific cost.

### 4. The figure, which is the part that was public

`F14_study_design.svg` carried `165,594 rows naive to every system` as a
hard-coded string, under a subtitle reading **"Counts are read from the frozen
artifacts, not transcribed."** It was the one count in that figure which was
transcribed, and it was transcribed from D036.

`fig_design` now takes `results/qc/predictor_comparison_all.json` as an
argument and derives all three quantities in that panel — the row count, the
predictor span and the CNN lead range — the way every other count in the figure
is already derived. The hard-coded literal is gone, so the figure cannot drift
from the artifact again.

Regenerating produced a one-line change in `F14_study_design.svg` and left the
other eight figures byte-identical. The manuscript, which states 165,574 in all
three places it appears and +0.1418 in its comparison table, needed no change.

### 5. What is not affected

The endpoint, the split, the preregistered rule, `predictor_comparison_all.json`
itself, `comparison_with_predictors_all.csv`, `contamination_all.json` and F13
are untouched. The recomputation wrote nothing into the repository; its outputs
were held outside the tree and compared against the frozen artifact.

**RESOLVED.** The discrepancy was 0.012% of the row set and moved no reported
quantity. It is corrected because the figure stated a published number that the
artifact did not support, and because a count that is derived cannot be
transcribed wrongly a second time.

---


## D051 — DTU Health Tech consent granted; §18 publishes by permission, within a stated scope · RESOLVED

**Opened and resolved:** 2026-10-12 · **Closes D040** and **retires the
withdrawal arm of D048**, neither edited beyond its status pointer · **Closes
L26**

**Decision: record the consent verbatim with its scope, publish §18 by
permission rather than by argument, retire the withdrawal, cancel the two
decision dates, and unblock the DOI.**

### 1. What arrived

Morten Nielsen replied on 2026-10-12 at 10:10 to the request D040 sent on
2026-10-11, copying `health-software@dtu.dk` and `health-master@dtu.dk`, under
the subject *"Re: Request for written consent to publish a NetMHCpan-4.1
benchmark (academic licence, §7(v))"*. The operative sentence, quoted exactly:

> "This is all fine. You can forward forward and published the results as
> described in your email below"

The repetition and the tense are in the original. The intent is unambiguous:
consent to publish the results the request described.

**This is written consent under §7(v).** The clause requires DTU Health Tech's
"prior written consent" to publish benchmark results to a third party. A reply
from the NetMHCpan corresponding author, to a request that quoted the clause and
enumerated what would be published, copied to two DTU Health Tech addresses, is
that consent.

### 2. The scope, which is the part that will be forgotten

Consent attaches to "the results as described in your email below", so the scope
is exactly what D040's request enumerated, and no more:

| Covered | Not covered |
|---|---|
| the average-precision comparison across five systems on the 165,574-row common set, NetMHCpan 4.1 at mean AP 0.5472 | the NetMHCpan software itself |
| per-peptide `Score_EL` and `%Rank_EL` for 199,978 rows, in `results/predictors/netmhcpan_4_1_test_scores.csv` | any part of its code or model files |
| | its verbatim program output, which `.gitignore` already excludes |

**Anything published from NetMHCpan 4.1 beyond those two items is outside this
consent**, including a benchmark on a different row set, a new metric, or the
raw stdout. A future analysis that extends the arm needs a fresh request. This
is recorded because a granted permission is easy to read as broader than it is.

### 3. Two things worth noting on the record

**The request quoted the corrected row count.** It states 165,574 rows and
199,978 scored rows — the artifact's figures, not the 165,594 that D036 and D048
carried until D050 corrected them this same day. The letter to DTU was right
while the decision log was wrong. That is luck, not process, and it is the
second time in two days that a transcribed count has been caught only by going
back to the artifact.

**The sender address is not a dtu.dk address.** The reply displays as
`Morten Nielsen <dtu-software@eirsciences.com>`, with the two DTU Health Tech
addresses in copy. Nothing here casts doubt on it — Morten Nielsen is the
NetMHCpan corresponding author (R2), the subject line is the thread's, and the
DTU addresses are copied. It is recorded because a consent record that does not
state what actually arrived is a weak record. **Required follow-up:** archive
the original message with full headers alongside the licence correspondence, so
the permission rests on a retained artifact rather than on a screenshot.

### 4. What changes

- **L26 closes.** It was the one item `FREEZE_RECORD.md` told readers of the
  public repository to know was unresolved. It is now resolved in the permitted
  direction.
- **The D048 withdrawal is not executed.** NetMHCpan 4.1 stays in §18,
  `results/predictors/`, the comparison and contamination artifacts, and F13.
  The computation is kept: it is the evidence that the decision carried no
  scientific cost, which is why the answer could be accepted whatever it was.
- **The dates are cancelled.** 2026-10-25 follow-up and 2026-11-08 decision no
  longer apply.
- **The Zenodo DOI is unblocked.** It was held only by this question.
- **No artifact changes.** No result, figure, score table or manifest entry is
  touched by this entry. Nothing was recomputed, because nothing depended on the
  answer.

### 5. What does not change

The scientific caveats D040 volunteered to DTU stand, and they were volunteered
rather than extracted: the comparison is not a like-for-like test of
presentation prediction, because the network was trained on this cohort and
NetMHCpan was not; training-set overlap with the test rows was measured rather
than assumed, and is reported per predictor. Consent removes a licensing
obstacle. It does not strengthen the comparison, and §18's wording is unchanged.

**RESOLVED.** §18 publishes by permission. The scope of that permission is in
§2 above, and it is narrower than "NetMHCpan results may be published".

---


## D052 — The verification environment is pinned; the training environment cannot be · RESOLVED

**Opened and resolved:** 2026-10-12 · **Stage 1 of the Q1 correction plan,
task Q1-006** · **Opens L27** · **Requested by the project owner**

**Decision: pin the environment that verifies results, record that the
environment that trained the checkpoints cannot be pinned retroactively, and
establish by measurement which of the two candidate causes of the
platform-confound irreproducibility is actually responsible.**

### 1. Why this came first

An audit on 2026-10-12 found that the platform-confound pair in
`results/qc/leakage_audit.json` — composition-only AUROC **0.6451** against a
random-halves control of **0.5150** — does not reproduce. Two causes were
candidates: hash-randomised set iteration order feeding a seeded sampler, and
drift between the environment that produced the artifact and the one now
present. **A corrected number computed under an unpinned environment would not
be verifiable either**, so the pin precedes the fix.

### 2. Four environments, not two

The audit said two. `ENVIRONMENT.md` in fact records three, and this entry adds
a fourth:

| `env_id` | Role | Python | numpy | torch |
|---|---|---|---|---|
| env-001 | local analysis; `RUN_LOG.md` cites it for run-001 to run-005 and **run-010, the leakage and confound audit** | 3.11.15 | 2.4.6 | none |
| env-002 | Colab; extraction for run-006, and training | 3.13.15 | 2.4.6 | 2.11.0+cu130, Tesla T4 |
| env-003 | Colab; later | 3.13.15 | **2.1.3** | 2.11.0+cu130, Tesla T4 |
| env-004 | verification, pinned by this entry | 3.14.4 | 2.4.6 | 2.14.1+cpu |

env-002 and env-003 differ in numpy and scipy version, which `ENVIRONMENT.md`
records without comment. **run-010 is the leakage and confound audit**, and it
is cited to env-001 — so the irreproducible pair was computed under Python
3.11.15 with numpy 2.4.6 and no torch.

### 3. Which cause is responsible — measured

Three quantities were recomputed under env-004, two of them deterministic by
construction and one of them the artifact in question:

| Quantity | Under env-004 | Verdict |
|---|---|---|
| primary endpoint, scored from the 25 stored checkpoints | 0.7550853623 against 0.7550853665 recorded | **−4.2e-09** — reproduced |
| sequence leakage over 2,000 splits: mean, median, min, max, p5, p95 | 14.59 / 14.62 / 11.76 / 17.25 / 13.14 / 15.96 | **exact** |
| predictor comparison on the common naive row set | 165,574 rows, prevalence to six decimals, four predictor intervals bit-for-bit, CNN 2.2e-09 | **exact** |

**What this does and does not establish.** Three quantities produced under
env-001/env-002/env-003 were reproduced under env-004: the primary endpoint
within the stated tolerance, and the sequence-leakage distribution and the
predictor comparison exactly. **These are cross-environment comparisons against
stored artifacts, not a test of every analysis under Python 3.11.15 and
3.13.15** — neither interpreter was executed here, and the remaining analysis
scripts were not re-run. **No general claim of version independence is made.**

What the evidence does support is narrower and sufficient for Stage 2's
purpose. The leakage distribution reproducing *exactly* is the informative
case: it is computed by the same script, in the same process, from the same
data, as the platform pair that does not reproduce. One half of
`leakage_audit.py` reproduces and the other does not, which locates the failure
inside the script rather than in the interpreter or the libraries. **The
platform-confound pair remains irreproducible and requires the deterministic
correction planned as Q1-001.**

**The remaining cause is the one the audit identified**: `by_unit` is a
`defaultdict(set)` of sequence strings, flattened by
`groups[key] += list(by_unit[u])` and sampled by `rng.sample(...)`. Python
randomises string hashing per process, so the list order differs between runs
and the fixed seed draws a different subsample. Part 1 is immune because its
only randomness is `rng.sample(units, k_test)` over a **sorted** list of unit
identifiers, and its result is a set-intersection size, which does not depend
on order.

Eleven draws were taken under env-004, running the unmodified script with only
its output path redirected and varying only `PYTHONHASHSEED` over 1 to 11:

| | frozen artifact | eleven draws |
|---|---|---|
| platform AUROC | **0.6451** | 0.6394 – 0.6433 |
| random-halves control | **0.5150** | 0.5150 – 0.5184 |
| excess over control | **+0.1301** | +0.1226 – +0.1277 |

**The frozen control value is reachable**: 0.5150 occurs exactly once among the
eleven draws, and is their minimum. The frozen AUROC and the frozen excess
remain above all eleven.

**Eleven draws do not characterise the distribution and do not establish
selection bias**, and none is claimed. Two readings are available and this
entry does not choose between them: the frozen values may be a tail draw from
the same distribution, or they may have been produced by a code or environment
state not reconstructed here. What is certain is narrower and sufficient — the
pair is **not reproducible**, and the corrected value and its stability are
Q1-001's business, under Stage 2, after which the question is moot because the
computation will have one answer.

### 4. What is pinned, and what is not

**Pinned.** `requirements.lock` is the complete transitive dependency set of
env-004 as `pip freeze --all` emitted it, 14 packages. `requirements.txt` keeps
the direct dependencies and now points at the lockfile. `ENVIRONMENT.md`'s "Not
yet pinned" section, which said a pin was deferred until the dependency set
stopped changing, is superseded.

**Not pinned, and not pinnable.** The 25 checkpoints were trained under
env-002/env-003: `torch 2.11.0+cu130` on a Tesla T4. This machine has no GPU
and no CUDA 13. **The checkpoints cannot be regenerated here and this entry
does not claim they can.** They are treated as hash-verified inputs, which is
what `freeze_manifest.json` already makes them. Scoring them under
`torch 2.14.1+cpu` reproduces the endpoint to −4.2e-09, which is accumulation
order across 25 models, not a change in any model.

### 5. A gap this exposed, recorded as L27

`RUN_LOG.md` carries run records for run-001 to run-006 and run-010 only.
**Model selection, the final fit, the endpoint read and the predictor
comparison have no run record at all**, and `final.json`, `endpoint.json` and
`selection.json` carry no field naming the versions that wrote them. The
checkpoints' environment is therefore *inferred* from env-002/env-003 rather
than recorded.

This changes no reported number — the endpoint and the predictor comparison
both reproduce under the pin — but it means "reproduce this in the original
environment" has no precise referent for the artifacts that matter most. It is
recorded as L27 rather than closed, because a run record cannot be written
retroactively for a run that was not logged. The forward fix is an environment
field in each result JSON, which belongs with Q1-008.

### 6. What did not work, recorded because it was tried

A faster equivalent of the platform measurement was written, replaying part
1's 2,000 `rng.sample` calls to advance the stream identically while skipping
its set unions, which consume no randomness. **It failed its own validation**:
at `PYTHONHASHSEED=1` it returned 0.6378 against the full script's 0.6396. The
stream-position assumption is therefore wrong in some way not identified, and
the shortcut was discarded rather than used. All draws quoted above come from
the unmodified script with only its output path redirected.

### 7. What changed in the tree

`ENVIRONMENT.md` (env-004 appended, pinning section superseded, the four-way
table and the run-record gap added), `requirements.txt` (rewritten to name both
files and the training-environment caveat), `requirements.lock` (new),
`LIMITATIONS.md` (L27 added). **No artifact, result, figure or score table is
touched**, and nothing was recomputed into the tree — the verification runs
wrote outside it.

**RESOLVED.** The environment under which results are verified is pinned and
its reproductions are recorded. The environment under which the model was
trained is documented and explicitly not reproducible. The cause of the
platform-confound irreproducibility is established as iteration order, not
version drift, which is what Stage 2 now acts on.

---


## D053 — The platform pair is made deterministic; the published value could not be reproduced · RESOLVED

**Opened and resolved:** 2026-10-12 · **Stage 2 of the Q1 correction plan, task
Q1-001** · **Corrects the method of D005 and D025's platform measurement
without disturbing their conclusions** · **Follows D052** · **Requested by the
project owner**

**Decision: fix the non-determinism in `leakage_audit.py` part 2, write the
corrected result to a new artifact rather than over the published one, carry the
corrected pair into `LIMITATIONS.md` L1 and figure F15, and leave the
contemporaneous gate record `QC_G5.md` unedited behind a supersession
pointer.**

### 1. The defect, located exactly

`results/qc/leakage_audit.json` recorded composition-only platform AUROC
**0.6451** against a random-halves control of **0.5150**, an excess of
**+0.1301**. D052 established that this pair does not reproduce and that the
cause is inside the script rather than in the interpreter or the libraries.
This entry identifies the mechanism.

**[FACT]** Peptides are held in `by_unit`, a `defaultdict(set)` of strings.
Three places flattened a set into a list — `groups[key] += list(by_unit[u])`
for the platform arm, and the two comprehensions building `ga` and `gb` for the
control. **Python randomises string hashing per process**, so each of those
lists came out in a different order on every run.

**[FACT]** `lda_auroc` splits its inputs **by position**:

```python
na, nb = len(XA)//2, len(XB)//2
trA, teA, trB, teB = XA[:na], XA[na:], XB[:nb], XB[nb:]
```

The first half trains and the second half tests. **List order therefore chose
the train/test split**, and a fixed `SEED` could not prevent it, because the
seed governs `rng.sample`'s selection and not the order of the sequence it
samples from. That is why one half of the script reproduced and the other did
not.

### 2. The fix, and why sorting does not bias it

`sorted()` is now used at each of the three flattening points. **`rng.sample`
still supplies the randomisation**, drawing a random subsample in random order
from a now-deterministic starting list, so the train/test split remains random
with respect to composition. Sorting fixes the starting point; it does not
order the data fed to the classifier. Had the sort reached `lda_auroc` directly
it would have been a serious defect, splitting peptides alphabetically and so
by first residue — a composition feature.

**[FACT] Determinism verified.** Three runs under `PYTHONHASHSEED` 1, 2 and 3
produce byte-identical output, sha256 `f38c8745b840f033…` in all three. Before
the fix no two runs agreed.

**[FACT] Part 1 is bit-for-bit unchanged.** All nine of its fields are
identical to the published artifact, `leakage_mean_pct` included at
14.592737536340957, as are both length distributions. This is the evidence that
the patch touched only the sampling path.

### 3. The corrected pair

| | published, v1 | **corrected, v2** | change |
|---|---|---|---|
| composition-only platform AUROC | 0.6451 | **0.6404** | −0.0047 |
| random-halves control | 0.5150 | **0.5170** | +0.0021 |
| excess over control | +0.1301 | **+0.1234** | −0.0067 |

**The finding stands.** The excess remains large and positive: composition
alone separates the two platforms far above a control that shuffles
participants instead. D005's and D025's conclusion — that platform is learnable
from peptide sequence, and that the endpoint is therefore a joint claim about
unseen individuals and unseen instrument conditions — is unchanged. What
changes is that the number supporting it can now be recomputed.

All three corrected values fall **inside** the eleven-draw ranges D052
recorded (0.6394–0.6433, 0.5150–0.5184, +0.1226–+0.1277). The published v1
values fall outside them on all three. This entry still does not claim to know
why; it records that the deterministic value is an ordinary member of the
distribution the defective code sampled from, and that the published one was
not.

### 4. What the gate never checked

**[FACT]** Freeze check 4 verifies 44 headline numbers against their artifacts.
`leakage_audit.json` is **not among the artifacts it reads**, so 0.6451, 0.5150
and +0.1301 appeared in `REPORT.md` without ever being gate-verified. Check 5
regenerates the figures from the artifact but does not re-run the script that
writes it. **Nothing in the nine checks would have failed at any point.** That
is the gap Q1-008 exists to close, and it is why this defect survived from
run-010 until an audit went looking.

### 5. What was written, and what was deliberately not

**Written.** `results/qc/leakage_audit_v2.json` (new, deterministic);
`scripts/leakage_audit.py` (three `sorted()` calls, a new output name, and a
docstring recording all of this); `scripts/make_figures.py` (reads v2; part 1's
fields are identical in both files, so only the platform panel moves);
`results/figures/F15_four_confounds.svg` (the three numbers);
`results/figures/F14_study_design.svg` (**its source caption only** — one line,
naming the file it read); `LIMITATIONS.md` L1 (the corrected pair, and a note
that the superseded one stood there until today).

**Not written, by decision.** `results/qc/leakage_audit.json` is **unmodified**.
It is the record of what was published and it cannot be regenerated by any
version of this code, which is itself the finding. `results/qc/QC_G5.md` keeps
its numbers and gains a supersession pointer: it is the contemporaneous record
of run-010 and reports what that run produced. **Rewriting a dated gate record
to show numbers that run never produced would be the same class of error this
project exists to catch.** `REPORT.md` is untouched under D041 and still states
the superseded pair; it is withheld, and the correction is recorded here and in
`LIMITATIONS.md`, which ships.

Seven of the nine figures regenerate byte-identically, verified before and
after.

**RESOLVED.** The measurement is deterministic, the published value is on the
record as irreproducible, and the conclusion it supported is unchanged.

---


## D054 — The external replication enters the tree, minus one input · RESOLVED as to promotion

**Opened and resolved:** 2026-10-12 · **Stage 3 of the Q1 correction plan, task
Q1-003** · **Precedes Q1-002, which cannot act on a script outside the
repository** · **Points D046** · **Requested by the project owner**

**Decision: commit the PXD004023 replication's code, run map and provenance;
commit no result; withhold `units.json` until the redistribution position is
established; and keep the raw payloads out of the tree under the rule the
registry already applies to S3 and S4.**

### 1. Why this was necessary

**[FACT]** D046's figures are cited in the manuscript Abstract, Results and
Discussion. **Nothing about that analysis was tracked** — no script, no input,
no result. Its only provenance was a session scratch directory under `/tmp`,
which is cleared without warning. An audit on 2026-10-12 found this and the
essential 1.3 MB was copied out the same day.

A manuscript claim whose code no longer exists cannot be defended in review,
and `/tmp` is not storage. That is the whole of the motivation; nothing
scientific changes in this entry.

### 2. What is committed

| Path | What it is |
|---|---|
| `scripts/fetch_px4023.sh` | retrieval: 160 header range requests, 37 containers, and a `verify` mode that re-hashes local headers |
| `scripts/label_px4023_runs.py` | raw header → instrument label; writes `runmap.csv` |
| `scripts/extract_px4023.py` | mzIdentML → accepted peptides per donor × workflow |
| `scripts/replicate_px4023.py` | the classifier, **in its original non-deterministic state** — see §3 |
| `data/external/PXD004023/runmap.csv` | 160 runs, each labelled instrument / year / fraction, all at `confidence=verified` |
| `data/external/PXD004023/perfile.json` | per-container accepted counts; **counts only, no sequences** |
| `data/external/PXD004023/header_checksums.txt` | SHA-256 of the first 1,048,576 bytes of all 160 acquisition files |
| `data/external/PXD004023/{raw,mzid}_manifest.txt` | the two file lists |
| `data/external/PXD004023/ANALYSIS_PLAN.md` | fixed **before** the classifier was run on this cohort |

Registered as **S8** in `DATA_SOURCES.md`, with run record **run-011**.

**64 KB in place of 162 MB.** The raw payloads stay out: the tracked payload is
110 MB, the headers alone are 161 MB and the containers 1.1 GB. This repository
does not archive raw payloads — `.gitignore` already carries `data/raw/**` — it
records what makes an absent payload verifiable. The owner took that decision
on 2026-10-12. `scripts/fetch_px4023.sh` retrieves both on demand and `verify`
checks the headers against the committed hashes.

### 3. The classifier is committed with its defect, deliberately

**[FACT]** `replicate_px4023.py` holds peptides in `set`s of strings and hands
a hash-ordered list to `rng.choice`. It is the same defect D053 fixed in
`leakage_audit.py`, and it means D046's figures are **one draw**: re-runs give
0.0579 to 0.0625 for the excess within the published 8–12 window, against the
0.0598 reported. Two further weaknesses travel with it — the control averages
**5** replicates and is quoted to four decimals, and nothing carries an
interval.

All of this is written into the script's own docstring, under a warning that
ends **"Do not cite output from this version."**

**Why not fix it here.** Q1-002 fixes it as a separate task so that its diff
shows exactly what changed, against code already under checksum. Promoting the
code as it ran, then correcting it in the open, is the same pattern D053 used
for the frozen audit: the superseded thing stays legible.

**No result artifact is committed.** Tracking D046's numbers now would put a
single draw under checksum and invite it to be cited.

### 4. The input that is withheld, and why

**`units.json` is not committed.** It holds the derived peptide sequences, 1.2 MB,
aggregated per donor × workflow. Two facts pull against each other:

- It **must** eventually be committed, because the 1.1 GB of containers was not
  preserved. Without it, reproducing the analysis requires re-downloading the
  deposit.
- Its redistribution position is **not established.** PXD004023 was not in
  `DATA_SOURCES.md` at all before today, S8's `license` field reads **NOT
  ESTABLISHED**, and S6 fixed the rule that redistribution terms are checked
  before any output file enters. `perfile.json` ships because it carries counts
  and labels, not sequences.

So it is withheld, declared absent in `scripts/check_references.py` with that
reason, and gitignored with a comment saying that lifting one line is the whole
of the change if the terms permit it. **The consequence is stated plainly: the
tracked analysis cannot be run end to end from the repository alone.**
`extract_px4023.py` rebuilds the file from the retrieved containers.

### 5. Two gaps recorded rather than closed

**[FACT]** The 37 containers were **not checksummed at retrieval**. Their
integrity rests on the 10 MB size floor in `extract_px4023.py` and on
successful XML parsing. That is not nothing — it is exactly what caught a
container which matched its declared byte count while containing
`<Error><Code>ConnectionClosedException</Code>` (D047) — but it is weaker than a
hash.

**[FACT]** PRIDE's published per-file checksums were **not collected**, so
nothing here is checked against the depositor's own record. The same limitation
L10 records for the PXD024871 metadata file.

**A third gap was found during review and closed rather than recorded.**
`runmap.csv` was first built ad hoc in the session that ran the replication, and
the labelling step was never written to a file. The committed table therefore
asserted `confidence=verified` and `evidence=raw header bytes 0-1048576` while
**nothing in the tree could reproduce it** — the same defect this stage exists
to fix, reproduced in miniature. `scripts/label_px4023_runs.py` now derives it,
reproduces the committed table **byte-identically** from the 160 headers, and
refuses to write when a header is missing or carries no unique model string.
It reads the file list from `raw_manifest.txt` rather than globbing, so a stray
file in `hdr/` cannot add a row.

**A defect in that generator was then found by reviewing it, and fixed before
it was committed.** The first version decoded each header as UTF-16LE from
offset 0 only. These headers are 1,048,577 bytes — an odd length — so a model
string at an odd byte offset was invisible to it, and a header carrying a
*second* model there would have been labelled `verified` on the one model the
decoder could see. That is a silent failure, not a safe one. The fix scans both
byte alignments. It was verified by constructing exactly that case: a real
header with `Q Exactive Plus` appended in UTF-16LE at an odd offset, which the
first version accepted silently and the current one refuses.

**What `confidence` means is now stated in the generator rather than implied.**
`verified` records that exactly one recognised model string was found in the
retrieved header. It is **not** verification by the depositor and **not**
agreement with anything PRIDE publishes; the SHA-256 in `header_checksums.txt`
are this project's own, computed from the bytes we received, and they detect
local corruption rather than establishing that those bytes are what was
uploaded. The word carried that implication without bounding it.

Six behaviours were tested, each with its precondition proven first: byte-
identical reproduction of all 160 rows, a missing header, a header with no
model string, two models at an odd offset, a header shifted by one byte, and a
stray file in `hdr/`. The shifted header is labelled rather than refused, which
is the intended division of labour: integrity is `fetch_px4023.sh verify`'s
job, not the labeller's.

### 6. What this does not claim

Instrument, acquisition year and SCX fractionation are perfectly confounded
across all 160 runs — 95 / 95 / 95 against 65 / 65 / 65, no exceptions. SCX
separates peptides by charge, a direct function of amino-acid composition,
which is the feature space the classifier uses. **This cohort cannot attribute
a signature to the instrument**, and nothing committed here describes it as an
instrument replication. `ANALYSIS_PLAN.md` says so and ships with the data.

Nor is this independent validation of the PXD024871 finding. The two cohorts
test different contrasts: platform nested in participant there, workflow paired
within donor here. They share a feature space, not a design.

**RESOLVED as to promotion.** The code and provenance are under checksum and the
analysis has a run record naming its environment. It is incomplete by one input,
by decision, and that is visible in the gate rather than silent. Q1-002 is now
unblocked.

---


## D055 — The replication is made deterministic and its control is given power · RESOLVED

**Opened and resolved:** 2026-10-12 · **Stage 4 of the Q1 correction plan, task
Q1-002** · **Supersedes the figures of D046**, which is not edited beyond its
status pointer · **Follows D054**, which put the code in the repository so this
could act on it · **Requested by the project owner**

**Decision: fix the non-determinism in `replicate_px4023.py`, raise the control
from 5 replicates to 200 and give every quantity an interval, decouple the two
arms' random streams, and replace D046's figures with the result.**

### 1. Three defects, not one

**[FACT] Defect 1, determinism — and it was in two places.** Peptides were held
in `set`s of strings, so the list handed to `balance()` came out in a different
order in every process and `rng.choice` drew a different subsample despite a
fixed seed. `units.json` already stores each value sorted, so holding them as
lists is both the fix and the simpler code.

Sorting the peptide collections was **not sufficient**. The control arm builds
its halves as `h1, h2 = set(p[:n]), set(p[n:])` — sets of *donor names* — and
iterating those is equally hash-ordered. After the first patch the per-donor
arm reproduced exactly while the control still varied, which is how the second
site was found: the three-seed test disagreed on control fields only. Both are
now sorted lists, and no `set(` remains in the script.

**[FACT] Defect 2, a control without power.** The control averaged **5**
replicates and was reported to four decimals. At 200 replicates its standard
error is **0.0034**; at 5 it was roughly 0.021, **larger than the effect it
bounds**. A four-decimal control on five draws was never meaningful.

**[FACT] Defect 3, coupled streams.** Both arms drew from one generator, so
raising the replicate count would have silently reshuffled the per-donor draws
as well. Each purpose now has its own stream through `scripts/seeds.py`, which
exists for exactly this (D010).

**[FACT] Determinism verified.** Three runs under `PYTHONHASHSEED` 1, 2 and 3
produce byte-identical output, sha256 `a447aeaf5b98379b…`. Before the fix no two
runs agreed.

### 2. What replaces D046

| | D046 | **D055** | change |
|---|---|---|---|
| 8–12 mean held-out AUROC | 0.6597 | **0.6604** | +0.0007 |
| 8–12 control | 0.5998 | **0.6135** | **+0.0137** |
| 8–12 excess over control | +0.0598 | **+0.0469** | **−0.0129** |
| all-lengths mean | 0.6582 | 0.6592 | +0.0010 |
| all-lengths control | 0.6039 | 0.6045 | +0.0006 |
| all-lengths excess | +0.0544 | **+0.0547** | +0.0003 |

**Intervals, which D046 had none of:**

| window | mean AUROC | control | excess |
|---|---|---|---|
| 8–12 | 0.6604, nominal-99% [0.6348, 0.6816] | 0.6135, se 0.0034, 200 replicates | **+0.0469 [+0.0194, +0.0699]** |
| all lengths | 0.6592, [0.6344, 0.6804] | 0.6045, se 0.0032, 200 replicates | **+0.0547 [+0.0294, +0.0778]** |

Both excess intervals exclude zero. **6 of 6 donors** sit above the control mean
in both windows, so the stop condition this stage set — a majority of donors
failing to exceed the control — was not triggered.

### 2a. What these intervals do and do not mean

Two limitations, recorded because an interval is easy to read as more than it
is. Neither is a defect in the computation; both bound its interpretation.

**[FACT] "Nominal" is doing real work in the label.** R6 measured nominal-95%
cluster-bootstrap intervals delivering **0.884–0.890** actual coverage at the
frozen conditions, which is why this project reports nominal-99% throughout and
never claims 99% confidence (D008, L5). **That measurement was made at ten
units. This analysis has six.** Coverage at six donors is worse and has **not**
been measured here. The intervals should be read as indicative width, not as
calibrated coverage.

**[FACT] The bootstrap itself is adequately resolved**, which is a separate
question from coverage. Six donors admit 462 distinct resample multisets, and
an independent 200,000-draw bootstrap reproduces the recorded 8–12 interval to
[0.6348, 0.6810] against [0.6348, 0.6816], with tail masses 0.00563 and 0.00434
against a nominal 0.005. The percentile estimate is not degenerate; it is the
coverage of the method at this n that is unverified.

**[FACT] The excess interval treats as independent two arms that are not.** The
AUROC arm resamples the six donors; the control draws random halves **of those
same six donors**, two hundred times. Resampling them independently ignores the
shared pool, and the direction of that error is **anti-conservative — the
excess interval is likely narrower than a correct one**. A joint procedure would
resample donors once and recompute both arms on the resample, which means
refitting the control inside every bootstrap draw; that was not run, and its
absence is recorded rather than glossed.

**What survives these caveats.** The point estimates and the 6-of-6 donor count
do not depend on any interval. The excess exceeds zero by a margin large
relative to the between-donor spread in both windows, and both windows agree.
The claim this analysis supports is the direction and approximate size of a
workflow signature, not a calibrated probability statement about it.

### 3. What actually moved, and what it means

**The per-donor arm barely moved: +0.0007 on the mean**, and no donor by more
than 0.0025. **The entire correction is the control, and only in the 8–12
window**, where it rose 0.5998 → 0.6135. Five draws had placed it low and the
published +0.0598 inherited that error.

The two windows now **agree**: +0.0469 and +0.0547. Under D046 they diverged,
+0.0598 against +0.0544, and **the divergent one was the window that got
published**. That disagreement was the visible symptom of a control with no
power, and it is gone.

**The finding survives, better specified and about 22% smaller.** A
composition-only classifier separates acquisition workflows in an independent
cohort, in 6 of 6 donors under leave-one-donor-out, with an interval excluding
zero. That is a stronger claim than the one it replaces, because it can be
recomputed and it carries its uncertainty.

### 4. What is unchanged

**The confound.** Instrument, acquisition year and SCX fractionation remain
perfectly confounded across all 160 runs, 95 against 65, with no exceptions.
SCX separates peptides by charge, a direct function of composition. **This
measures acquisition workflow and cannot attribute a signature to the
instrument**, and `results/replication/px4023.json` carries that sentence in its
own `caveat` field.

**The comparison with PXD024871.** The excess, not the raw AUROC, is the
comparable quantity, because donors are more separable in this cohort than
participants are in ours. The honest comparison is now **+0.0469 against
+0.1234** (D053's corrected platform excess), not +0.0598 against +0.1301.
Both terms of that comparison have changed since the manuscript was drafted.

**The method.** Composition features, Fisher LDA, midrank AUROC, class balance
by subsampling, leave-one-donor-out — all unchanged. `comp`, `lda`, `auroc` and
`balance` are untouched apart from `balance` taking its generator explicitly.

### 5. Why no single-cause delta is quoted

The numbers differ from D046 for three reasons at once: determinism, decoupled
streams and the replicate count. **No attribution to one of them is offered,
because none would be honest.** D046's value was itself one draw from a
distribution, so there is no stable figure to difference against. The
replacement is stated as a replacement, not as a correction of a known
quantity.

### 6. What was written

`scripts/replicate_px4023.py` (two `sorted()` fixes, `N_CONTROL = 200`,
per-purpose streams, intervals, and a JSON report); **`results/replication/px4023.json`,
the first tracked result for this analysis**. `SUPPLEMENTARY_METHODS.md` S6.5
and S6.6 and the four citation sites in `MANUSCRIPT_MCP.md` carry the new
figures; both documents are private and unpublished.

**`units.json` remains uncommitted** under D054 §4, so this artifact cannot be
regenerated from the repository alone — the same standing as the 25 model
checkpoints, and stated in the script's own docstring.

**RESOLVED.** The replication is deterministic, its control has power, every
quantity carries an interval, and D046's figures are superseded rather than
quietly amended.

---


## D056 — Recurrence is a perfect label oracle, and it is worth more than the floor · RESOLVED

**Opened and resolved:** 2026-10-12 · **Stage 5 of the Q1 correction plan, task
Q1-004** · **A fourth construction defect, of the family D044 recorded three
of** · **Requested by the project owner**

**Decision: quantify the oracle with the repository's own metric, report it
under both tie conventions because it is tie-dependent, annotate the QC check
that created it, and change no frozen artifact.**

### 1. The construction

**[FACT]** From `POSITIVES.csv` and `NEGATIVES.csv`:

| | rows | unique sequences | max multiplicity |
|---|---|---|---|
| positives | 520,000 | 466,946 | **15** |
| negatives | 520,000 | **520,000** | **1** |

Positive/negative sequence overlap: **0**. Negatives were drawn without
replacement across the whole 52-participant dataset, so **no decoy sequence
occurs twice**; positives recur whenever two participants observed the same
peptide.

**[FACT]** On the held-out partition, 15,988 of 100,000 test positives have a
sequence that occurs somewhere in training. **Of 100,000 test negatives, zero
do.** Therefore

```
P(label = 1 | sequence seen anywhere in training) = 1.000000
P(label = 1 | sequence seen nowhere in training)  = 0.456557
```

Not approximately one. Exactly one, with no counter-example in 520,000
negatives. **`results/qc/QC_G4.md` records "Negatives globally unique —
520,000 distinct" as a *passing* check**, and that pass is the mechanism.

### 2. What the oracle is worth, and why two numbers are reported

A classifier scoring 1 for "seen in training" and 0 otherwise, using **no
sequence features at all**, evaluated per participant and averaged under D008:

| tie convention | mean per-participant AP | nominal-99% |
|---|---|---|
| file order (`kind='stable'`, as `train_cnn.average_precision` sorts) | **1.0000** | [1.0000, 1.0000] |
| **random tie-breaking, 200 draws per unit** | **0.6426** | **[0.6205, 0.6620]** |

**The 1.0000 is an artefact and must not be quoted.** The score takes two
values, so 184,012 test rows tie at zero, and a stable sort breaks that tie by
file order. The test rows are assembled positives-first, so inside the tie block
every positive precedes every negative and the ranking is perfect by
construction of the file, not of the data. **0.6426 is the convention-free
quantity.**

**[CORRECTION]** An audit on 2026-10-12 put this figure at **0.5799** using an
ad-hoc block-averaging tie rule. That was an underestimate and is withdrawn.
The figure is 0.6426.

### 3. Why it matters

**0.6426 exceeds the preregistered composition floor of 0.597, and exceeds the
0.636 floor recomputed on the endpoint's own population (D044 defect A).** A
lookup table with no features, measuring only what the dataset construction
gives away, scores above the baseline the endpoint is gated against.

This does **not** mean the network relies on it. **The oracle shows the shortcut
exists and is exploitable; it does not show it was exploited**, and attributing
any part of 0.7551 to it would need an experiment this is not.

What it does bound is the meaning of the floor. A floor is supposed to say what
is achievable without learning the task. On this construction, something
achievable without reading the peptide at all clears it.

### 4. What is unaffected

The leakage-free sensitivity arm already excludes every recurring test positive,
so **that arm is untouched by this defect**. The primary endpoint is not: it
scores all 100,000 test positives, including the 15,988 the oracle identifies
for free.

### 5. What was written

`scripts/recurrence_oracle.py` and `results/qc/recurrence_oracle.json`, both
new; an annotation on `results/qc/QC_G4.md`; limitation L28. **No frozen
artifact is modified**, nothing is retrained, and the endpoint is unchanged.

**RESOLVED as to measurement.** The conditional is exact and the AP is reported
under the convention that does not depend on row order.

---

## D057 — The leakage comparison is 88% prevalence, and the trainer said otherwise · RESOLVED

**Opened and resolved:** 2026-10-12 · **Stage 5 of the Q1 correction plan, task
Q1-005** · **Corrects a causal attribution printed by `train_cnn.py`** ·
**Requested by the project owner**

**Decision: hold prevalence fixed and re-measure, report the decomposition,
correct the trainer's wording, and claim no causal attribution for what
remains.**

### 1. The defect

**[FACT]** The leakage-free subset is built by dropping the 15,988 test
positives whose sequence occurs verbatim in training. **It drops positives
only.** Prevalence therefore falls from **0.500000** to **0.456321**.

**[FACT]** Average precision has the prevalence as its own floor: a random
classifier scores AP equal to the positive fraction. So the **floor** moves by
**0.0437** on its own, and the two arms are not comparable.

**[FACT]** `scripts/train_cnn.py` printed that difference as
`Inflation from leakage: +0.0495`. **Two things change between the arms and the
difference was labelled as one of them.**

### 2. The decomposition

Rescored from the 25 frozen checkpoints, subsampling negatives per participant
so the leakage-free arm carries the same positive fraction as the primary arm,
50 independent subsamples per participant:

| | mean per-participant AP | prevalence |
|---|---|---|
| primary | **0.7551** | 0.500000 |
| leakage-free, as reported | **0.7056** | 0.456321 |
| **leakage-free, prevalence-matched** | **0.7386** | 0.500000 |

The observed drop decomposes exactly one way, and only one:

```
(P − L)  =  (P − M)  +  (M − L)
 0.0495  =   0.0165  +   0.0330
```

| | | share of the drop |
|---|---|---|
| observed drop, primary − leakage-free | **+0.0495** | |
| **prevalence effect**, matched − leakage-free | **+0.0330** | **66.6%** |
| **residual**, primary − matched | **+0.0165** | **33.4%** |

**Two thirds of the reported "inflation from leakage" is prevalence.** One third
survives at matched prevalence.

### 2a. A correction to this entry's own first draft

**[FACT]** The random-classifier floor shift — 0.500000 − 0.456321 = **0.0437**
— is **not** a share of the observed drop, and an earlier draft of this entry
divided it by the drop and reported **88.2%**. That is withdrawn.

The two quantities are different. The floor shift says how far the **baseline**
moves, because a random classifier scores AP equal to the positive fraction. The
prevalence effect says how far **this model's** AP moves when prevalence is
restored. They are not equal, because the CNN is not a random classifier and its
AP does not track the floor one-for-one. The arithmetic is decisive:

```
floor shift + residual  =  0.0437 + 0.0165  =  0.0602   ≠  0.0495
(M − L)     + residual  =  0.0330 + 0.0165  =  0.0495   =  0.0495
```

Only the second closes. **The floor shift explains why the arms are
incomparable; it does not measure the effect**, and it is recorded in the
artifact as `random_classifier_floor_shift` with a note saying so, rather than
as a share.

### 3. What this does and does not establish

**Establishes:** a gap survives at equal prevalence. Removing recurring
positives costs something beyond the arithmetic of the positive fraction.

**Does not establish that the residual is caused by leakage.** The leakage-free
subset is also a **different and plausibly harder set of peptides** — those
unique to a single participant — so matching prevalence removes one confound,
not all of them. **No causal attribution is made for the 0.0165**, and the
artifact says so in its own `what_this_does_not_show` field.

### 4. What was corrected

`train_cnn.py`'s line now reads **"Primary − leakage-free"**, a difference
rather than a cause, with a pointer to this entry. The number it prints is
unchanged. `LIMITATIONS.md` L2 carries the decomposition.

**[FACT] Neither arm's recorded value changed.** The rescoring reproduces
0.7551 and 0.7056 from the frozen checkpoints; the matched arm is a third
measurement placed beside them, not a replacement for either.

### 5. What was written

`scripts/prevalence_matched.py` and `results/qc/prevalence_matched.json`, both
new; the trainer's print statement; L2. **No frozen artifact is modified**, and
nothing is retrained — the checkpoints are read.

**RESOLVED.** The comparison is decomposed, the causal wording is gone, and what
remains is reported as a residual rather than an effect.

---


## D058 — The decoy exposure is bounded, and D044's estimate survives it · RESOLVED as to the AP cost

**Opened and resolved:** 2026-10-12 · **Stage 6 of the Q1 correction plan, task
Q1-009b** · **Tests, and confirms, D044 defect B** · **Requested by the project
owner**

**Decision: replace the assumption D044 flagged with a measurement, bound the
cost adversarially rather than estimating it, record what the bound does not
cover, and leave one discrepancy unresolved rather than explaining it away.**

### 1. What was open

D044 defect B measured that `build_dataset.py` rejects candidate decoys found in
`observed`, accumulated across all 52 participants including the ten held out.
It estimated the cost at **−0.0030 AP**, under an explicit assumption — uniform
sampling from the *unique* eligible pool — which it flagged as imperfect,
because the code reservoir-samples k-mer *occurrences* and then deduplicates,
with the direction of the bias unestablished.

**That estimate is the entire basis for treating defect B as an extension rather
than a release blocker.** An estimate resting on an unvalidated assumption is a
weak basis for that decision.

### 2. The flagged assumption is worth 0.0009%

**[FACT]** The proteome was re-retrieved and its SHA-256 matches the S5
provenance record exactly — `64299d01…`, 7,728,297 bytes — so the k-mer space is
the one the frozen dataset was built from. The reconstruction reproduces D044's
universe (**2,658,972**), its test-only total (**364,900**), and **all five
per-length test-only counts and negatives-drawn counts exactly**.

**[FACT]** Both weightings, computed rather than assumed:

| | expected false negatives | of 520,000 |
|---|---|---|
| unique-weighted (D044's assumption) | **4264.0** | 0.820% |
| occurrence-weighted (what the reservoir samples) | **4259.3** | 0.819% |
| **difference** | **4.7** | **0.0009%** |

**The ambiguity D044 could not resolve is numerically negligible.** This
confirms D044's estimate; it does not overturn it.

**[FACT]** The trivial assumption-free count bound — every eligible test-only
peptide drawn — is **361,740, or 69.6% of the negative pool**. It is vacuous,
and reported so the reader sees why the bound belongs on the AP cost at a
bracketed count rather than on the count alone.

### 3. The bound, and why it is a bound

Writing average precision over positives *i* as

```
AP = (1/P) · Σ_i  t_i / (t_i + n_i)
```

where *t_i* counts positives ranked at or above *i* and is **invariant** under
any change to the negatives, and *n_i* counts negatives above *i*: AP is
strictly decreasing in every *n_i*. Deleting a negative ranked below *i* leaves
*n_i* alone, while deleting one above it lowers *n_i* and **raises** AP — so the
minimal-help deletion is the *k* lowest-scoring negatives. And no insertion
raises every *n_i* by more than one placed above all positives.

**The pair therefore minimises AP at that k.** It is a guaranteed upper bound on
the loss, not an adverse scenario. An exhaustive search over removal strategies
(lowest / random / highest) crossed with insertion strategies (top / median /
bottom / random) confirms the claimed construction attains the minimum.

Inserted scores are `max + 1.0`, strictly greater than every real score, so
`kind='stable'` never interleaves them and no tie convention is engaged.

**[FACT]** At **k = 82 false negatives per unit** — 4264 across 52 units, which
is D044's 81.6 by the same arithmetic:

| | mean per-participant AP | nominal-99% | delta |
|---|---|---|---|
| base | 0.755085 | [0.7373, 0.7718] | — |
| **realistic insertion** | 0.751942 | [0.7342, 0.7685] | **−0.0031** |
| **worst case** | **0.724961** | **[0.7078, 0.7411]** | **−0.0301** |

**The realistic case reproduces D044's −0.0030 at −0.0031.** The two answer
different questions and neither supersedes the other: D044 estimated what would
happen, this bounds what could.

### 4. The preregistered decision survives

**[FACT]** The worst-case interval's lower end, **0.7078**, clears the
preregistered threshold of **0.647** by **+0.0608**.

**[FACT] That interval is a SENSITIVITY interval, not a calibrated confidence
bound**, and the entry says so wherever it appears. It is a cluster bootstrap of
the *perturbed* per-unit values, so it carries the bootstrap's own
under-coverage at ten units — R6 measured nominal-95% delivering 0.884–0.890,
which is why nominal-99% is used throughout — and it is **conditional on exactly
82 false negatives in every unit**. The realised per-unit count is a random
draw and units above 82 fare worse.

**[CORRECTION]** A first draft of this work reported a worst-case lower bound of
**0.7067**, obtained by subtracting the worst-case delta from the recorded CI
lower bound. **That is not a valid bound on the perturbed estimand** and is
withdrawn. Bootstrapping the perturbed per-unit values directly gives 0.7078.
The withdrawn figure happened to be more conservative by 0.0011, but
conservative by accident is not the same as correct, and it was labelled a
confidence bound, which it was not.

### 5. An unresolved discrepancy

**[FACT]** This reconstruction's eligible pool is smaller than D044's at every
length, by **49,589 to 50,015** — a near-constant offset:

| L | D044 pool as built | this reconstruction |
|---|---|---|
| 8 | 9,905,950 | 9,856,225 |
| 9 | 9,685,563 | 9,635,548 |
| 10 | 9,783,092 | 9,733,122 |
| 11 | 10,031,599 | 9,981,790 |
| 12 | 10,249,119 | 10,199,530 |

The constancy rules out the two obvious explanations. The expressed-protein
count differs — **20,158 here against 20,152** elsewhere in this log — but six
extra proteins would push the pool *up*, not down. Skipping k-mers with
non-standard residues would scale with length, not stay flat.

**D044's audit was run outside this repository and its script is not available,
so the definitional difference cannot be settled from the evidence here.** It
propagates to k as **+0.5%** (4264.0 against 4242.5), which changes no
conclusion. It is recorded as **UNRESOLVED**, in the entry and in the artifact's
`d044_comparison.status` field, rather than explained away.

### 6. What this does and does not license

**Supported.** The weighting ambiguity is numerically negligible under the
reconstructed definitions. The worst case bounds the AP cost at a given k. The
preregistered decision survives that worst case with margin.

**Not supported.** That every assumption in D044 is harmless — one sensitivity
analysis does not establish that. That the construction is acceptable in
principle — **it remains non-test-blind, and a bounded cost is not no defect.**
That the bound is unconditional — it is conditional on k per unit, and on the
AP estimand alone.

**Demoting defect B to an extension is justified on the AP cost**, now by a
bound rather than an estimate. The defect itself is not closed, and L-entries
for it stand.

### 7. What was written

`scripts/decoy_exposure_bound.py` and `results/qc/decoy_exposure_bound.json`,
both new. **No frozen artifact is modified**, nothing is retrained, and the
endpoint is unchanged. The proteome is retrieved on demand and not committed;
its checksum is verified against S5 before use and the script refuses if the
UniProt release has rotated.

**RESOLVED as to the AP cost.** The estimate D044 could not validate is
confirmed, bounded, and scoped.

---


## D059 — The gate learns to regenerate, not only to hash · RESOLVED

**Opened and resolved:** 2026-10-12 · **Stage 7 of the Q1 correction plan, task
Q1-008** · **Closes the gap that let D053's defect survive** · **Requested by
the project owner**

**Decision: add a tenth check that re-runs each classified script and compares
its artifact, run it always on `--write` and on request otherwise, and require
every script to be classified so a newcomer cannot slip in unexamined.**

### 1. The gap, stated precisely

**[FACT]** The nine checks hash outputs. Check 5 regenerates the figures *from
stored JSON*; check 8 compares file hashes to a manifest *written from the same
tree*. **No check re-ran the script that wrote the JSON.**

**[FACT]** `leakage_audit.py` part 2 was non-deterministic from run-010
(2026-10-06) until D053 (2026-10-12). **Every one of the nine checks passed on
every day of that period.** The gate proved the artifact had not been tampered
with, which was true and useless: the artifact had never been reproducible.

A hash proves a file has not changed. It says nothing about whether the file
could be produced again. Those are different properties and the gate only had
the first.

### 2. Three classes, and why the distinction is load-bearing

**BYTES** — deterministic on tracked inputs, no model scoring. Must regenerate
byte-identically. This is where the hash-ordering defect class lives and where
the check has teeth. Four scripts: `union_analysis.py`,
`negative_diagnostic.py`, `recurrence_oracle.py`, **`leakage_audit.py`**.

**NUMERIC** — scores the 25 frozen checkpoints. torch accumulates in a
non-associative order, so byte-identity is **not achievable**: the endpoint
reproduces to −4.2e-09 and `endpoint_by_length` to **2.2e-08**, measured while
building this check. Compared at a tolerance of 1e-6 instead — four orders of
magnitude above the observed drift and far below any real change. Two scripts:
`endpoint_by_length.py`, `prevalence_matched.py`.

**Demanding byte-identity for the NUMERIC class would produce a gate that fails
for a reason nobody can fix, which is worse than no gate.**

**EXEMPT** — 31 scripts that cannot run from tracked inputs alone, or must never
run. Each carries its reason in `scripts/regen_check.py`. `build_dataset.py` and
`build_split.py` are exempt because they would **rebuild the preregistered
artifacts** that check 2 exists to prove have not moved; `train_cnn.py` because
the checkpoints are hash-verified inputs trained on hardware this environment
does not have (D052); the predictor and PXD004023 scripts because their inputs
are licensed, withheld, or gigabytes.

**An exemption is a claim.** They are listed so a reader can dispute them,
rather than being invisible by omission.

### 3. The check must have been seen to fail

**[FACT]** Three failure modes were exercised, each with its precondition
proven first:

| injected | result |
|---|---|
| D053's fix reverted — `sorted(by_unit[u])` → `list(by_unit[u])` | `FAIL leakage_audit.py NOT byte-identical (833 -> 832 bytes)`, exit 1 |
| an unclassified script added to `scripts/` | `FAIL unclassified script(s): ['zz_newcomer.py']` |
| an artifact deleted | `FAIL union_analysis.py artifact missing` |

**The first is the exact defect that escaped for six days.** The gate now
catches it in 93 seconds.

**[FACT]** The classification is complete: 37 scripts, 6 regenerable, 31 exempt,
0 unclassified. An unclassified script **fails** the check — the same discipline
check 5 applies to figures, for the same reason: a count silently accepts a
newcomer, a named set does not.

### 4. Cost, and where it is paid

**[FACT]** The full check is **208 seconds**, against 3–5 for the other nine.
That cost is real and would not be paid on every invocation, so it is placed
where the claim is made:

- `--verify` runs the fast nine and **skips** check 10, saying so.
- `--verify --regen` runs all ten.
- **`--write` always runs all ten**, and refuses to freeze if any fail.

Freezing is the moment the repository asserts a verified state. **That is the
moment the assertion should be tested**, not three minutes earlier at the
reader's discretion.

### 5. Safety

**[FACT]** Each script writes to its real artifact path, so the check snapshots
the bytes before the run and restores them in a `finally`. For a healthy
deterministic script the restore is a no-op; for a failing or interrupted one it
guarantees the tree is not left modified. Verified: after the full run and after
all three injected failures, `git status` showed no modified file.

**No preregistered artifact can be touched**, because the two scripts that write
them are exempt by name and the check never invokes them.

### 6. What this does not do

It does not prove the exempt scripts reproduce — **31 of 37 are outside it**,
and the reasons are stated rather than the coverage overstated. It does not
prove the NUMERIC pair is deterministic, only that it agrees within 1e-6. And it
cannot catch a defect that is deterministic and wrong; it catches
irreproducibility, which is a narrower thing.

**RESOLVED.** The gate now tests that artifacts can be made, not only that they
have not moved.

---


## D060 — The invariants get tests, and the tests get defects · RESOLVED

**Opened and resolved:** 2026-10-13 · **Task Q1-009** · **Builds on D059** ·
**Requested by the project owner**

**Decision: assert the dataset's scientific invariants in a read-only suite,
separate properties that must hold from known defects pinned at their measured
size, and require every test to be demonstrated failing against an injected
defect before it counts as a test.**

### 1. What was open

**[FACT]** Every construction defect this project has found was found by a
person reading code: the negative pool drawn with knowledge of the held-out
participants (D044 defect B), the recurrence oracle (D056), the prevalence
confound (D057), the non-deterministic audit (D053). D059 closed the gap
between "the tree has not moved" and "the artifacts can be made again". Neither
gate asks whether what they protect is correct. For a study whose subject is
construction defects, finding them by audit rather than by test is the
methodology the manuscript criticises.

### 2. What was built

`tests/test_invariants.py` — 11 tests over the frozen artifacts, 21 injected
defects, a runner at `tests/run.sh`, and a CI invocation at
`.github/workflows/invariants.yml`. The eleven failure modes Q1-009 names are
mapped to tests in the module docstring; the map is deliberately not
one-to-one, because "split disjointness and stability" is two claims and
"label and preprocessing leakage" fails in two different ways.

**Two kinds of assertion, kept apart.** PROPERTY (T03, T04, T06–T11) is
something that must hold or the study does not mean what it says; a failure is
a bug. MAGNITUDE (T01, T02, T05) pins a **known defect at its measured size**,
so that drift is loud in either direction. **Pinning a defect is not endorsing
it.** T05 asserts that 82,900 sequences were withheld from the decoy pool
*using held-out information* — it asserts the defect is still exactly that
large, and `LIMITATIONS.md` L2 is where the defect is argued.

**Read-only by construction.** The suite contains no write primitive. Its only
subprocess call is `git ls-files`. Injections replace fields of a frozen
dataclass rather than mutating a shared snapshot, so no injection can
contaminate a later result; this was verified by fingerprinting the snapshot
across all 21 injections and re-running the baseline afterwards. The CI job
asserts `git status --porcelain` is empty after the run.

### 3. Two defects found in the tests themselves

**[FACT]** The first draft of T08 recomputed the recurrence oracle against
`per_unit_ap_file_order`, which is **exactly 1.0 for every participant** —
`POSITIVES.csv` precedes `NEGATIVES.csv` and a stable sort leaves every
remaining positive ahead of every negative. The test was reproducing a
constant and passed against an injected defect. This is the artefact D056
warns about, met from the other direction.

It was replaced with a closed-form expectation of AP under random tie-breaking,
derived from the hypergeometric position distribution within each tie block.
It gives **0.642600** against the artifact's 200-draw Monte Carlo **0.642631**
— D056's headline number now confirmed by a second, non-simulated method.

**[FACT]** That still could not catch a single-row defect, and the reason is
structural: one flipped row moves E[AP] by about **6e-05**, below the **~1e-04**
noise the stored Monte Carlo carries at 200 draws. **No tolerance against that
artifact can see one row.** The fix was exact integer recomputation of the
oracle's conditional counts, which move by one when one row moves. **That exact
check is the primary one and must not be replaced by the tolerance comparison**;
the closed form is additional evidence, not a substitute.

### 4. New findings

**[FACT]** The realised split's exact train/test overlap is **15.988%**, which
**exceeds the 95th percentile of 2,000 random splits (15.958%)** recorded in
`leakage_audit_v2.json`. The chosen split leaks more than most random splits
would, not less.

**[FACT]** **402 leak-free test positive rows (0.479%)** are one substitution
from a training positive. The leakage-free subset removes exact matches only;
near-duplicates were never measured before. Recorded as L29.

**[FACT]** `TEST_LEAKFREE.csv` holds **84,012 rows** over **82,900 distinct
sequences** — 1,112 sequences occur in two held-out participants each.
`train_cnn.py` and `prevalence_matched.py` read the file into a **set keyed by
sequence** and apply it to rows keyed by (unit, sequence). The two keyings
select the same 84,012 rows, because a sequence absent from training is absent
for every participant. T01 asserts that equivalence, which is load-bearing and
not obvious.

**[FACT]** **181 positive rows over 165 distinct sequences** contain B, X or Z;
**no decoy does**, because decoys are alphabet-filtered and observed peptides
are not. Pinned in T06.

### 5. What was deliberately not done

The 21-injection suite is **not** wired into `freeze.py` as an eleventh check.
It costs about three minutes and duplicates what CI does on every push.

**[FACT]** `freeze.py --verify` **cannot serve as a lightweight CI integration
check**, for two reasons that are structural rather than about cost.
`freeze.py:70` reads `REPORT.md` through `R = lambda p: (REPO/p).read_text()`,
and `REPORT.md` is **untracked** under D041 — a fresh clone has no such file,
so checks 3 and 4 raise `FileNotFoundError` rather than failing cleanly. And
check 5 is **not read-only**: it executes `make_figures.py`, overwriting all
nine SVGs in place, with **no `finally` restore** of the kind `regen_check.py`
carries, so an interrupted run leaves drifted bytes and nothing to restore
them. Cost is not the obstacle — `make_figures.py` imports only `json` and
`pathlib`. **No change was made to `freeze.py`.** Closing this would require
either tracking `REPORT.md` or making checks 3 and 4 conditional on its
presence, and neither was authorised.

### 6. What this does not do

It does not test the model. Nothing here retrains, scores a checkpoint, or
touches `train_cnn.py` beyond reading its outputs; the trainer's own selftest
is freeze check 9. It does not prove the dataset is free of defects — it
asserts the defects that are known and the properties that were thought to
check. **A defect nobody has imagined still has no test.** And the suite's
sensitivity against any Monte Carlo artifact is bounded by that artifact's own
precision, which §3 states rather than hides.

**RESOLVED.** The invariants are asserted, and every assertion has been seen to
fail.

---

## D061 — Correction to the commit message of `6719f50` · RESOLVED

**Opened and resolved:** 2026-10-13 · **Erratum to D060, task Q1-009** ·
**Corrects a commit message, not a result**

**[CORRECTION]** The commit message of `6719f50` reads:

> one flipped row moves E[AP] by 6e-09 less than the Monte Carlo's own 1e-04
> noise

**That phrase is wrong in two ways.** The magnitude is **approximately 6e-05**,
not 6e-09 — a factor of 10,000 — and the relation is **"below"**, not "less
than", which as written does not parse. The sentence should read: *one flipped
row moves E[AP] by approximately 6e-05, below the Monte Carlo's own
approximately 1e-04 noise.*

The point the sentence was making is unaffected and is stated correctly in
**D060 §3**: a single-row defect moves the expected AP by less than the noise
carried by the artifact's 200-draw estimate, so no tolerance-based comparison
against `recurrence_oracle.json` can detect it. That is why the **exact integer
recomputation** of the oracle's conditional counts is the primary check in
`tests/test_invariants.py` T08, with the closed-form expectation beside it as
corroboration rather than as a substitute.

**Nothing computed changes.** No scientific artifact, figure, result or
preregistered file is touched by this entry, and no number reported anywhere
moves. `6719f50` and `8238987` are preserved exactly; git history is **not**
rewritten, because the record of what was written is worth more than a tidy
message, and because an amend would invalidate `8238987`, whose
`parent_commit` field names `6719f50`.

**Consequence for the freeze.** This entry edits `DECISION_LOG.md`, a tracked
file, so its recorded SHA-256 in `freeze_manifest.json` no longer matches the
tree. **The manifest written at `8238987` is stale as of this commit** and the
project's declared rule — the two-commit freeze — calls for a re-freeze. That
re-freeze was **not** authorised here and has **not** been performed. The
manifest itself is unmodified; `tests/test_invariants.py` T10 fails on the one
changed digest until a re-freeze is run, and that failure is expected and
correct rather than a defect.

**RESOLVED.** The inaccurate phrase is identified and corrected in the
append-only record.

---

## D062 — The negative pool is size-biased, and it does not matter · RESOLVED

**Opened and resolved:** 2026-10-13 · **From the independent methodology audit
of 2026-10-13** · **Two reporting corrections and one measured null result**

An end-to-end audit re-derived the pipeline from first principles rather than
from its own description. It produced two reporting corrections, one confirmed
implementation defect whose consequence turned out to be immeasurably small, and
one open concern closed by measurement. Everything below was recomputed from the
frozen artifacts during the audit.

### 1. The cross-participant recurrence figure was understated by 1.73×

**[CORRECTION]** `build_dataset.py:131` computes `shared = npos - len(allpos)`
and prints it as *"53,054 of 520,000 rows (10.20%) are sequences also positive
in another unit"*. `FREEZE.json` records the same number under the accurate key
`cross_unit_duplicate_rows`, and the manuscript carried the printed wording.

For a sequence present in *k* participants, `npos - len(allpos)` contributes
*k−1*. It is the count of **excess occurrences**, not of rows. Recomputed from
`data/derived/POSITIVES.csv`:

| quantity | value | share of 520,000 rows |
|---|---|---|
| positive rows | 520,000 | — |
| distinct positive sequences | 466,946 | — |
| excess occurrences (the 53,054 figure) | 53,054 | 10.203% |
| sequences present in >1 participant | 38,767 | — |
| **rows whose sequence is in >1 participant** | **91,821** | **17.658%** |

The published sentence described the 91,821 quantity and quoted the 53,054 one.
A third figure is also correct and must not be confused with either: **20.1%**
of the observed *union* occurs in more than one participant
(`union_stats.json`: 2,124,276 of 2,658,972 occur in exactly one), which is the
figure `build_dataset.py`'s own comment cites from run-006.

**Corrected in the manuscript**, which now leads with 91,821 rows (17.66%) in
both the Methods and Results passages and retains 53,054 (10.20%) explicitly
labelled as the excess over one occurrence each, stating which question each
answers. **`FREEZE.json` is not touched**: its key name was already accurate and
it is a preregistered artifact.

**Why it matters.** Cross-participant recurrence is one of the four confounds the
study is about, and the stated justification for the D003 leakage-free subset.
The figure of record understated the exposure by a factor of 1.73. No computed
result consumed 10.20% as an input, so nothing downstream moves.

### 2. The matched threshold is an interval, and the decision clears all of it

**[FACT]** D008's threshold of 0.647 is the preregistered rule and is not
revised. The matched floor on the frozen dataset is 0.636, and §2 of the D057
entry already recorded that a floor-plus-0.05 threshold built from it is
**0.6860 point, nominal-99% [0.6557, 0.7173]** — an interval, because the floor
is itself an estimate over ten participants.

The manuscript reported both floors and the preregistered threshold but never
stated the consequence: the primary nominal-99% lower bound of **0.7368 exceeds
0.6860 and also exceeds 0.7173**, the upper end of the matched threshold's own
interval. The decision is therefore invariant to which floor is used, including
against the least favourable reading of the matched one.

**Added to the manuscript.** This strengthens the primary result and costs
nothing, since it revises no threshold and introduces no new analysis.

### 3. The negative pool is size-biased over distinct sequences

**[CORRECTION]** `build_dataset.py`'s docstring states that *"Reservoir sampling
gives the same uniform draw in bounded memory."* It does not. Lines 104–127 run
Algorithm R over the stream of eligible k-mer **occurrences**, so the reservoir
is uniform over occurrences; lines 129–136 then deduplicate with
`dict.fromkeys`. Uniform-over-occurrences followed by deduplication is
**size-biased sampling over distinct sequences**: a k-mer occurring *m* times in
the proteome has roughly *m* times the chance of entering the pool.

**[FACT]** Measured. Proteome multiplicity of the frozen negatives against the
multiplicity of a uniform draw over distinct eligible k-mers, all five lengths:

| L | frozen mean | frozen frac >1 | frozen max | uniform-over-distinct baseline |
|---|---|---|---|---|
| 8 | **1.8474** | 12.99% | 1181 | 1.0966 |
| 9 | **1.5561** | 11.22% | 787 | 1.0835 |
| 10 | **1.5243** | 10.45% | 700 | 1.0755 |
| 11 | **1.4954** | 9.65% | 621 | 1.0692 |
| 12 | **1.4668** | 9.09% | 557 | 1.0638 |

The bias is confirmed at every length, running 1.38× to 1.68× above baseline and
worst at length 8. Negatives are therefore enriched for repeated, paralogous and
low-complexity sequence, whose amino-acid composition is atypical.

**[FACT] It changes nothing measurable.** A replacement pool was drawn uniformly
over distinct eligible k-mers with everything else held identical — the same
per-participant length profile taken from the frozen positives, 1:1 ratio, global
uniqueness, exclusion of every observed peptide, and the same expressed-protein
restriction — under seed 20261013 so it cannot be confused with the frozen draw.
All five of `build_dataset.py`'s integrity checks pass on it, and its own
multiplicity matches baseline at every length, which is what makes it a valid
comparator.

| arm | negatives | mean per-unit AP | nominal-99% CI |
|---|---|---|---|
| composition-only floor | frozen (control) | **0.6361** | [0.6042, 0.6669] |
| composition-only floor | uniform redraw | **0.6350** | [0.6041, 0.6666] |
| endpoint, 25 frozen checkpoints | frozen (control) | **0.7551** | [0.7368, 0.7721] |
| endpoint, 25 frozen checkpoints | uniform redraw | **0.7558** | [0.7378, 0.7735] |

**Floor delta −0.0011. Endpoint delta +0.0007**, the latter in the opposite
direction to the inflation the audit anticipated. Both are roughly a fiftieth of
their own interval widths. Both controls reproduce the record: the floor returns
0.6361 against the 0.6360 in D057 §2, and the endpoint returns 0.7551 with its
published interval exactly — on `torch 2.14.1+cpu` against the original
`2.11.0+cu130`, which makes the control an incidental independent reproduction of
the headline endpoint in a different environment.

**Why the bias is inert.** Multiplicity-enriched sequences are 9–13% of the pool,
and amino-acid composition averaged over 8–12 residues is not shifted enough by
that minority to move the 20-dimensional LDA direction. The network, which reads
positional structure rather than composition alone, is equally unaffected.

**The audit's own expectation is withdrawn.** It reasoned that the floor and the
endpoint "may both be inflated by a shared cause". Measurement does not support
that, and it must not reach the manuscript. What remains is a docstring that
misdescribes a sampling property, recorded as **L30**.

**Scoring was inference only.** The 25 checkpoints were loaded read-only; nothing
was retrained, no split was rebuilt, and the preregistered endpoint was neither
recomputed nor replaced. The redraw is a sensitivity beside it.

### 4. File-order tie-breaking is negligible on the endpoint

**[FACT]** `train_cnn.average_precision` sorts with `kind='stable'`, and `load()`
reads `POSITIVES.csv` before `NEGATIVES.csv`, so exact score ties resolve in
favour of positives. D056 established that this convention is fatal for the
recurrence oracle, whose score takes two values and whose file-order AP is
therefore 1.0.

Counted on the endpoint: **41 exact score ties across all ten held-out
participants in 200,000 rows** for the first of the 25 models, 42 on the redraw.
That is 2×10⁻⁴ of rows, and only a tie straddling the label boundary can bias AP
at all, so the worst-case effect is below 10⁻⁴ AP. The concern is closed; the
oracle's exposure to the same convention is unaffected and remains as recorded in
D056.

### 5. What was examined and found sound

Recorded because the audit was asked to be balanced, and because these were
checked rather than assumed. All six preregistered checksums in
`PREREGISTRATION.md` recomputed and matched. Leakage recomputed from the frozen
artifacts at 15,988 of 100,000 test positive rows, 15.988%, with 84,012
leakage-free — matching `SPLIT_FREEZE.json` and the manuscript. The D057
decomposition verified additive to the last digit: 0.0165222843 + 0.0329844561 =
0.0495067404. Configuration E=16/C=32/k=3/p=0.0 confirmed as the grid maximum in
`cv_results.json`. The power analysis's use of AUROC to parameterise a binormal
effect size for an AP endpoint confirmed as a legitimate parameterisation, not a
metric mismatch. The apparent conflict between the manuscript's 165,574 rows and
`predictor_comparison.json`'s 175,524 resolved as two genuinely different row
sets, the five-system and three-system naive intersections, with no error.

### 6. What was deliberately not changed

- **`build_dataset.py` is untouched.** Its docstring misdescribes the draw, but
  the file is frozen and checksummed, and editing it to fix prose would change a
  preregistered artifact's digest. The misstatement is recorded in **L30** and in
  this entry instead. Correcting the docstring is a separate decision.
- **No frozen artifact, figure or preregistered file is modified.** `FREEZE.json`,
  `SPLIT_FREEZE.json`, `POSITIVES.csv`, `NEGATIVES.csv`, `SPLIT.csv`,
  `TEST_LEAKFREE.csv` and every file under `results/` are as they were.
- **The preregistered endpoint stands at 0.7551 [0.7368, 0.7721]** against the
  threshold of 0.647. Nothing in this entry revises it.

**Consequence for the freeze.** This entry edits `DECISION_LOG.md` and adds a row
to `LIMITATIONS.md`, both tracked files, so their recorded SHA-256 values in
`freeze_manifest.json` no longer match the tree. **The manifest written at
`e94225c` is stale as of this commit**, and the project's two-commit freeze rule
calls for a re-freeze. That re-freeze is **not** authorised here and has **not**
been performed. The manifest itself is unmodified;
`tests/test_invariants.py` T10 fails on the two changed digests until a re-freeze
is run, and that failure is expected and correct rather than a defect.

**RESOLVED.** Two reporting corrections applied to the manuscript, one
implementation defect recorded with its consequence measured as null, one concern
closed.

---

## D063 — τ was assumed at 0.25 and is measurably 0.097 · RESOLVED

**Opened and resolved:** 2026-10-13 · **From the audit of 2026-10-13, item
A-16** · **Adds a sensitivity beside D008; revises nothing**

### 1. What the audit got wrong first, recorded because it was wrong

**[CORRECTION]** The audit's original item A-03 claimed the power figures quoted
in the manuscript — 0.98 at a true AUROC of 0.75, 0.42 at 0.70 — were stale,
resting on the reconstructed per-participant counts of 120–600 recorded in
`results/power/power_params.json` rather than on the realised 10,000.

**That claim was wrong, and is withdrawn.** It traced the figures to
`power_grid.csv` without opening `results/power/decision_rule.json`, which is
the artifact that produced them and closed D008. That artifact is correctly
specified for the preregistered rule: `ratio: 1`, `floor: 0.597`, and
`adopted_rule` reading *"reject if the lower bound of the nominal-99% cluster
bootstrap interval > 0.647"*, with `power_at_nominal_99` giving 0.42 at AUROC
0.70 and 0.978 at 0.75. The `ratio=10` and prevalence-floor rejection the audit
objected to belong to `power_grid.csv` grid 2, a supporting resolution analysis
the manuscript does not quote.

Recomputed independently at ratio 1, prevalence 0.5, nominal 99%, 10,000
positives per participant and τ = 0.25, rejecting on `lo > 0.647`: **0.420 at
AUROC 0.70 and 0.976 at 0.75**, against the artifact's 0.42 and 0.978. The
record reproduces. The residual count difference — `npos_sim: 1500` against the
realised 10,000 — is immaterial, which confirms rather than assumes the
project's standing argument that the between-participant term dominates.

### 2. What survives: τ is now measurable, and it is 2.6× smaller than assumed

**[FACT]** `POWER_ANALYSIS.md` states that τ, the between-participant SD of
latent discrimination, is *"unknown and unmeasurable before data exist"* and
sweeps it at 0.10 / 0.25 / 0.50, with every figure conditional on the choice.
D008 adopted 0.25.

Inverting the binormal model on the ten realised per-participant average
precisions in `results/model/endpoint.json`:

| quantity | value |
|---|---|
| realised per-participant AP | mean 0.7551, sd 0.0225 |
| implied per-participant *d* | mean 1.0110 |
| **τ realised** | **0.0965** |
| τ assumed by D008 | 0.25 |

**[FACT]** Power against the **unchanged** preregistered threshold of 0.647,
recomputed at both values:

| τ | AUROC | true AP | power vs 0.647 | CI half-width |
|---|---|---|---|---|
| 0.0965 (realised) | 0.70 | 0.6891 | **0.980** | 0.0183 |
| 0.0965 (realised) | 0.75 | 0.7416 | 1.000 | 0.0173 |
| 0.25 (assumed) | 0.70 | 0.6875 | **0.420** | 0.0472 |
| 0.25 (assumed) | 0.75 | 0.7390 | 0.976 | 0.0426 |

At the effect size the manuscript singles out to argue that failure to reject
would not be evidence of absent signal, **power is 0.98 rather than 0.42**, and
the interval is 2.6× narrower than the planning value. The study is better
resolved than its own figures claim, and the direction of the error is
conservative: a reader told power is 0.42 cannot over-read a rejection.

### 3. What this does not do

**D008 is not revised.** The threshold stays 0.647, the rule stays the rule of
record, and the 0.42 / 0.978 figures remain the preregistered power statement.
`calibrate_decision_rule.py` is untouched and remains EXEMPT in
`regen_check.py` for the reason already recorded there: re-running it cannot
change a threshold already frozen. The endpoint is not recomputed. Nothing in
this entry moves a preregistered number.

**Two limits travel with the estimate**, and are written into the artifact
rather than left to a reader to infer. τ is estimated from ten held-out
participants and carries its own uncertainty, so it is an estimate and not a
constant. And the inversion assumes the binormal model, which
`POWER_ANALYSIS.md` already flags as *"a convenience"* rather than a prediction;
these figures inherit that caveat. Both are stated in the manuscript paragraph
as well.

### 4. The artifact and its gate

`scripts/tau_realised.py` writes `results/power/tau_realised.json`, holding τ,
the per-participant APs and their implied *d*, the four power cells, both
caveats, and an explicit statement of what it does not revise. The script reads
only tracked inputs and is deterministic at a fixed seed: two consecutive runs
produce byte-identical output.

It is classified **BYTES** in `scripts/regen_check.py`, so the freeze gate
regenerates it and compares byte-for-byte. Adding it required editing
`regen_check.py`, which is the discipline that file describes — *"a count
silently accepts a newcomer, a named set does not"* — and the reason an
unclassified script fails the check rather than being skipped.

This was done because the manuscript now quotes τ = 0.097 and a power of 0.98.
A number in the manuscript with no artifact behind it is the defect this project
has already recorded once, and it is not repeated here.

**RESOLVED.** A-03 withdrawn as not an error; τ measured, with power against the
unchanged threshold recomputed beside the preregistered figures.

**Consequence for the freeze.** This entry edits `DECISION_LOG.md`, adds
`scripts/tau_realised.py` and `results/power/tau_realised.json`, and edits
`scripts/regen_check.py` — all tracked. The manifest written at `56dd11f` is
stale as of this commit and a re-freeze follows under the two-commit rule.

---

## D064 — The margin that chose the decoy set supports no ranking · RESOLVED

**Opened and resolved:** 2026-10-13 · **From the audit of 2026-10-13, items
A-04 and A-05** · **Adds an interval D002 did not report; revises nothing**

D002 selected negative set C over set A on composition-only AUROC **0.6085
against 0.6120**, a margin of 0.0036 reported as a point estimate with no
interval, and with the diagnostic's second metric pointing the other way:
`total_abs_divergence_pp` is 10.258 for C against 10.046 for A. The audit raised
two questions and a structural concern. One question is answered against the
original reporting, the concern is refuted by measurement.

### 1. The margin is not distinguishable from zero

**[FACT]** Paired bootstrap over the held-out diagnostic rows, B = 10,000,
nominal 99%, positives shared between arms because they are literally the same
60,000 peptides, each arm's negatives resampled independently:

| contrast | point | nominal-99% interval | |
|---|---|---|---|
| set A − set C | **+0.0036** | **[−0.0024, +0.0092]** | **crosses zero** |

**The 0.0036 that selected the negative construction supports no ranking of the
two candidates.** D002's choice is not thereby wrong: its stated rationale is
that decoys drawn from the same expression context as the positives are the
harder and more honest set, and that argument stands on its own. What cannot be
claimed is that the diagnostic's numbers established it. The manuscript now says
so, and quotes the interval.

**The preregistered construction is not revised.** Set C remains the negative
set. Nothing in this entry changes the frozen dataset, the split, or the
endpoint.

### 2. The structural concern is refuted

**[CORRECTION]** The audit observed that `negative_diagnostic.py` builds set C
from a restricted source set — `if len(src) > 4000: break`, probed with only
`obs_sample[:2000]` — while `build_dataset.py` builds the real negative pool
from every protein yielding at least one observed 8–12mer, which is 20,152 of
20,652. It inferred that the diagnostic may have tested a population the
pipeline did not build, and that since the implemented pool covers 97.6% of the
proteome it might behave like the **rejected** set A.

**Measured, and it does not.** A fourth set, C′, was drawn from the
20,152-protein population using the same draw procedure, so source population is
the only thing that differs from C:

| set | source proteins | AUROC | divergence |
|---|---|---|---|
| A | all proteins ≥13 aa | 0.6120 | 10.046 pp |
| C (the tested set) | **1,908** | 0.6081–0.6085 | 10.243–10.258 pp |
| C′ (the built population) | **20,152** | **0.6078** | **9.831 pp** |

C′ − C is **−0.0004**, nominal-99% [−0.0064, +0.0055]. The source population
barely matters, and C′ carries the **lowest** compositional divergence of the
three, so on the diagnostic's second metric the pool actually built is the best
of the three rather than the worst. That also dissolves the audit's secondary
observation that the two metrics disagreed: they disagree for the tested proxy,
not for the thing that was built.

**Two figures in the audit's own text were wrong and are corrected here.** It
read the `len(src) > 4000` cap as binding and reported "~4,001 source proteins".
The cap never binds: only **1,908** of roughly 20,000 proteins of length ≥13
contain one of the 2,000 probe peptides, so the proxy is more restricted than
the audit claimed, and the measured irrelevance of that restriction is
correspondingly stronger. An intermediate run reported 1,925, which was a draw
that did not reproduce the frozen set C; see §4.

### 3. The expression restriction is weak, and is now described as weak (A-05)

**[FACT]** `FREEZE.json` records `expressed_proteins: 20152` of
`proteome_sequences: 20652`. The restriction to proteins that yielded at least
one observed peptide therefore excludes **500 proteins, 2.42%**. With 2,658,972
peptides observed across 52 participants, nearly every protein contributes at
least one 8–12mer, so a constraint described as confining decoys to expressed
protein in practice confines them to almost the whole proteome.

The counts were already in the manuscript; the consequence was not. It is now
stated there, and it explains §1: two candidate sets drawn from populations that
overlap almost completely should not be expected to differ measurably, and they
do not.

### 4. The artifact, and what it took to make it honest

`scripts/negset_margin.py` writes `results/qc/negset_margin.json` and is
classified **BYTES** in `scripts/regen_check.py`.

**An interval on the wrong draw is worse than no interval.** The first version of
the script rebuilt sets A and C without building set B. `negative_diagnostic.py`
builds B between them and consumes the `random.Random` stream doing so, so
skipping it shifted the probe sample and produced a set C at AUROC 0.6081 from
1,925 source proteins — a valid draw from the same construction, but **not the
preregistered one**. The margin it gave, +0.0039 [−0.0020, +0.0096], was an
interval on a fresh draw rather than on D002's comparison.

The script now reproduces that stream consumption and **asserts** that both arms
match `results/qc/negative_diagnostic.json` to within 1e-12 before the bootstrap
is allowed to run. With that in place set C returns 0.6084513 and divergence
10.258 pp, identical to the frozen diagnostic, from 1,908 source proteins. The
assertion is the difference between an interval on the preregistered margin and
an interval on something adjacent to it.

The estimator was also checked rather than swapped on faith: the bootstrap uses
scipy's C `rankdata` for speed, and the script asserts it agrees with
`negative_diagnostic.auroc`, which computes the same midranks in a Python loop,
to within 1e-12 on every point estimate. Measured agreement on the benchmark was
exactly 0.0, at 5.04 ms against 72.4 ms per call.

C′ is deliberately **not** in the gated artifact. It needs a four-minute
proteome scan that would nearly double the freeze's runtime, and it answers a
one-off audit question rather than anything the manuscript states. It is recorded
here with its method, as D062 recorded the uniform redraw.

**RESOLVED.** The margin is reported with its interval and described as
supporting no ranking; the expression restriction is described as weak; the
concern that the diagnostic tested the wrong population is measured and refuted;
D002 and the frozen dataset are unchanged.

**Consequence for the freeze.** This entry edits `DECISION_LOG.md`, adds
`scripts/negset_margin.py` and `results/qc/negset_margin.json`, and edits
`scripts/regen_check.py` — all tracked. The manifest written at `ec814a0` is
stale as of this commit and a re-freeze follows under the two-commit rule.

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
