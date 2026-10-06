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
| D008 | Decision rule for §25 — effect size and threshold, replacing "better than chance" | G13 |
| D009 | Preregistration freeze mechanism (commit hash + timestamp) | G8 |
| D010 | Seed convention — 20261006 is today's date; record the convention or replace it | G8 |
| D011 | Unit definition: participant as the independent unit, with replicates and fractions nested within it, versus treating replicates as units. Sets the resampling unit and therefore the width of every uncertainty interval. Raised by `METHODOLOGY.md` M2 | G3 |
| D012 | Partial typing: units with fewer recorded alleles than loci are ambiguous between a genuine single-allele locus and incomplete reporting. Imputation is prohibited; the question is whether such units are excluded from allele-stratified analyses or retained with a flag. Raised by `METHODOLOGY.md` M4 | G2 |
| D013 | S2 retrieval route: the metadata file as deposited in the submission, versus the separately maintained community-annotation repository. Different authorship, version history, and checksum availability, and possibly different contents. Settled by reading the S1 manifest, not by guessing a path. Raised by `DATA_SOURCES.md` | G1 |

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
