# QC_G5 — leakage and confound audit

run-010, on the frozen dataset, before the split exists. Measures what the split
will have to handle rather than checking a split already made.

| Result | Check | Detail |
|---|---|---|
| **FAIL** | Sequence leakage under unit-disjoint split | **14.59% mean** of test positives also appear in training |
| **FAIL** | Instrument separable from sequence | composition-only AUROC **0.6451** vs 0.5150 control |
| PASS | No negative is observed | verified at freeze |
| PASS | Positive/negative disjoint | verified at freeze |
| n/a | Preprocessing fitted on training only | no preprocessing is fitted; encoding is fixed |

Both failures are properties of the data, not defects in the build. Neither is
correctable; both must be handled by design and declared.

## 1. Unit-disjoint splitting does not prevent sequence leakage

Over 2,000 random 10-unit test partitions:

| | % of test positives also in training |
|---|---|
| mean | **14.59%** |
| median | 14.62% |
| range | 11.76% – 17.25% |
| 5th–95th pct | 13.14% – 15.96% |

This is **higher than the 10.20% row-level duplication** reported at freeze, and
the difference matters. A test unit's sequences get 42 independent chances to
appear among the training units, so exposure compounds with the number of
training units rather than staying at the pairwise rate.

**Unit-disjointness and sequence-disjointness are different properties**, and
the proposal's §9 treats them as if satisfying the first delivers the second. It
does not. Roughly one test positive in seven has been seen verbatim during
training.

## 2. The instrument is learnable from the peptides themselves

| Comparison | composition-only AUROC |
|---|---|
| LTQ-unit vs Lumos-unit positives | **0.6451** |
| random half of units vs other half (control) | 0.5150 |
| **excess attributable to platform** | **+0.1301** |

The control is the important part. Generic unit-to-unit variation gives almost
nothing — 0.515, barely above chance — while platform gives 0.645 **from amino
acid composition alone, with no positional information.** The signal is specific
to the instrument, not a by-product of units differing from one another.

The length profile shows one visible mechanism: 12-mers are 11.69% of LTQ
positives against 9.85% of Lumos, a 1.83 pp difference, consistent with
different detectability across the mass range.

**This escalates D005 from a design limitation to a measured one.** D005
established that platform cannot be separated from unit by any split. This shows
the peptides carry a platform signature a trivial model can read, so a model
evaluated on held-out units is partly being tested on **platform transfer**, and
the §25 claim inherits that at a now-quantified magnitude.

## Consequences for the split (G6)

**Platform stratification becomes mandatory, not advisory.** Train and test
partitions must carry matched platform proportions. That does not remove the
confound — nothing can, since no unit spans both platforms — but it stops the
split from silently becoming a platform split, which at 0.645 separability would
be a substantial artefact.

**A cross-platform transfer analysis is now worth preregistering.** Train on the
25 LTQ units, test on the 27 Lumos units, and the reverse. That measures the
confound's magnitude directly instead of inferring it. If performance collapses
across platforms while holding up within them, the §25 claim is substantially
about instrument rather than biology — and that is a result worth having before
the interpretation is written, not after.

## What remains clean

Negatives were drawn from a global expressed-protein pool, assigned to units by
length profile only, so they carry no unit-specific or platform-specific signal
by construction. Any unit or platform signal the model finds comes from the
positive class. Worth stating because it also means a unit's negatives are not
drawn from that unit's own expressed proteins — a mismatch that is deliberate
(it keeps negatives unit-agnostic) but should not be mistaken for per-unit
matching.
