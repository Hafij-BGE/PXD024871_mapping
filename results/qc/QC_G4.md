# QC_G4 — analysis dataset frozen

run-009. Built by `scripts/build_dataset.py` from the preregistered decisions,
with no parameter chosen at build time.

| Result | Check | Detail |
|---|---|---|
| PASS | Positives are observed | all 520,000 drawn from the extracted universe |
| PASS | No negative is observed | zero intersection with the 2,658,972 observed sequences |
| PASS | Positive/negative disjoint | zero overlap |
| PASS | Negatives globally unique | 520,000 distinct |
| PASS | Class ratio | exactly 1:1 (D002) |
| PASS | Length profiles match | per-length counts identical between classes |

**Frozen at commit `74c5f12f`.** Checksums in `data/derived/FREEZE.json`. Nothing
downstream may read a dataset whose checksum does not match that record.

## Composition

| | |
|---|---|
| Units | 52, each contributing exactly 10,000 positives |
| Positives | 520,000 rows · 466,946 distinct sequences |
| Negatives | 520,000 rows, all distinct |
| Source proteins for negatives | 20,152 of 20,652 (97.6%) yielded ≥1 observed peptide |
| Sampled from a universe of | 2,658,972 — the cap discards 80% of available positives |

The two files are byte-identical in size. That is a consequence of the design,
not a coincidence to explain away: equal row counts and exactly matched
per-length profiles give equal total sequence bytes. Their checksums differ.

## The number the split rule has to handle

**53,054 positive rows (10.20%) are sequences that are also positive in another
unit.** 466,946 distinct sequences across 520,000 rows.

These are **retained, not deduplicated.** They are precisely the exposure D003
governs, and removing them here would hide the leakage question rather than
answer it — a split that never sees them cannot be shown to handle them. The
split rule (G6) must state explicitly whether a sequence positive in a training
unit may also appear in a test unit.

The first build aborted on this, because I had written "positives globally
unique" as a pass/fail check. That was wrong: run-006 measured 20.1% of the
universe in more than one unit, so cross-unit duplication is expected structure,
not corruption. The check is now a reported statistic. The abort was still the
correct behaviour — it refused to write anything until the question was
settled.

## Decisions applied, none chosen at build time

| Decision | Applied as |
|---|---|
| D024 | 10,000 per unit, length-stratified, seed 20261006 |
| D002 | set C negatives — expressed-protein, unobserved; ratio 1:1 |
| D004 | no confidence filter; 99.29% of the union is top level, so it is a no-op |
| D011 | unit = participant |

## What this dataset cannot support

**The floor is not chance.** A composition-only linear model reaches AP **0.597**
against these negatives (`negative_diagnostic.json`). Reported performance must
be stated against that, and D008's threshold is set relative to it.

**Negative labels are not evidence of non-presentation.** Set C members may be
presented and merely undetected; run-006 measured 1.45× redundancy with the last
unit still 55% novel, so these repertoires are deeply undersampled. The negative
class is contaminated at an unknown rate, biasing measured performance downward.

**The instrument confound is untouched by anything here.** D005 remains an
accepted limitation: the two platforms partition the 52 units 25/27 with zero
overlap, so no split over units separates platform from participant.

## Next

G5 (leakage and confound audit) then G6 (split). G6 needs D003's split rule
written against the 10.20% figure above, and D009 and D010 closed.
