# DECISION_LOG

Methodological decisions for the PXD024871 CNN experiment. Append-only.
Each entry is traceable: what was decided, why, what it changes, who/when.

Status values: OPEN / RESOLVED / PERMANENT

---

## D001 — Carry HLA genotype into the dataset schema

**Date opened:** 2026-10-06
**Status:** OPEN
**Blocks:** Phase A2 (file map), Phase B (dataset), G2
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

## D002 — Select the negative-control strategy

**Date opened:** 2026-10-06
**Status:** OPEN
**Blocks:** Phase B (dataset), G4, §15 primary endpoint
**Affects sections:** §8, §15, §16, §18, §20

**Question**
Which of the proposal's three candidate negative constructions (§8 A/B/C) is
primary, and at what positive:negative ratio?

**Why this is a blocker**
The negative set defines what the classifier is being asked to discriminate,
so it sets the ceiling and the meaning of every metric downstream. It also
interacts with §15: the AUPRC baseline is the positive prevalence, so an
unfixed class ratio makes the primary endpoint uncomparable to any other
number, including our own secondary analyses. §8 currently lists the three
options and selects none.

**Risk specific to each option**
- Set A (reference-derived, length-matched) — the easiest to generate, and
  the most prone to inflation: background composition differs from observed
  ligands, so a model can separate the classes on composition alone and score
  well without learning anything position-specific.
- Set B (decoys) — composition can be controlled by construction, but decoys
  may be trivially separable in a different way, and overlap with the positive
  set must be excluded explicitly.
- Set C (hard negatives, resembling positives but unobserved) — the most
  informative discrimination and the most defensible against the inflation
  critique, but "unobserved" conflates genuine non-presentation with limits of
  detection, which must be stated as a limitation rather than resolved.

**Open sub-decision**
Fixed positive:negative ratio (e.g. 1:1, 1:10, 1:100). Must be locked in
preregistration and reported next to every AUPRC. A ratio chosen after seeing
performance invalidates the endpoint.

**Recommendation:** Decide A/B/C on a composition diagnostic run *before*
training — compare per-position and overall composition of each candidate
negative set against the positives — and prefer the construction that is not
separable on composition alone. Record the diagnostic as the evidence for the
choice.

**What must be true before this can be marked RESOLVED**
- One primary strategy named, with the composition diagnostic attached.
- Class ratio fixed and written into the preregistration.
- Rejected options retained here with their reason.
- Exclusion of positive/negative overlap specified as a G4 check.

**Next step:** Cannot run the diagnostic until Phase B yields a positive set.
Decide the *decision procedure* now (above), execute it at G4.

---

## Pending — not yet written up as entries

Raised in review, still unlogged. Each needs its own entry before the gate it
blocks:

| # | Decision | Blocks |
|---|---|---|
| D003 | Cross-donor shared sequences: drop from one split, or allow and report both ways | G5 |
| D004 | Identification-confidence threshold for the positive set; whether to re-filter stricter than deposited | G4 |
| D005 | Instrument as a confound — two instrument platforms in the class-I runs; check against donor assignment | G5 |
| D006 | Training-set overlap between the comparison predictors and these peptides; handling rule if overlap exists | G11 |
| D007 | Minimum-N gate: preregistered eligible-positive threshold below which the confirmatory arm does not run | G4 |
| D008 | Decision rule for §25. **Form now fixed by D014 (ratified)**: a lift over prevalence, tested on the interval's lower bound. Magnitude still open and cannot close before D002, since prevalence follows the class ratio | G6, after D002 |
| D009 | Preregistration freeze mechanism (commit hash + timestamp) | G8 |
| D010 | Seed convention — 20261006 is today's date; record the convention or replace it | G8 |
| D011 | Unit definition: participant as the independent unit, with replicates and fractions nested within it, versus treating replicates as units. Sets the resampling unit and therefore the width of every uncertainty interval. Raised by `METHODOLOGY.md` M2 | G3 |
| D012 | Partial typing: units with fewer recorded alleles than loci are ambiguous between a genuine single-allele locus and incomplete reporting. Imputation is prohibited; the question is whether such units are excluded from allele-stratified analyses or retained with a flag. Raised by `METHODOLOGY.md` M4 | G2 |
| D013 | S2 retrieval route: the metadata file as deposited in the submission, versus the separately maintained community-annotation repository. Different authorship, version history, and checksum availability, and possibly different contents. Settled by reading the S1 manifest, not by guessing a path. Raised by `DATA_SOURCES.md` | G1 |
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
total runs, 48 hours wall clock, 4 cores, no GPU, ~2 GB peak extraction disk.
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
2. **Streaming the containers is forced, not chosen.** 30 GB writable disk
   against a container set described as ~47.8 GB: the full set cannot be held.
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
