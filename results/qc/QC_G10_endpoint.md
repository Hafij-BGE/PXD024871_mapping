# QC_G10 — the endpoint

run-015. The held-out partition was read, once, on 2026-10-07. 10 units,
200,000 rows, 25 models, none of which had seen it.

## Result

| | mean per-unit AP | nominal-99% CI | per-unit range |
|---|---|---|---|
| **PRIMARY — full test partition** | **0.7551** | **[0.7368, 0.7721]** | 0.7102 – 0.7911 |
| SENSITIVITY — leakage-free (D003) | 0.7056 | [0.6926, 0.7184] | 0.6796 – 0.7269 |
| SECONDARY — score-ensembled (D027) | 0.7651 | — | — |

Reference points, both fixed before the read: composition-only floor **0.597**,
decision threshold **0.647**.

## Decision

**The null is rejected.** The primary lower bound, 0.7368, exceeds the
preregistered threshold of 0.647.

**It is also rejected on the leakage-free subset**, where the lower bound is
0.6926 — still above 0.647. This is the more important of the two statements:
the result does not depend on peptides the models had already seen.

Lift over the composition floor: **+0.158** primary, **+0.109** leakage-free.
Both exceed the 0.05 preregistered margin.

## Leakage inflates the primary by 0.0495

The gap between the two figures is the inflation, measured on this split rather
than assumed. It is substantial — roughly a third of the apparent lift over the
floor — and it is precisely why D003 required both be reported. A study
reporting only the primary would have overstated the effect by that much
without any way for a reader to know.

## A bug was found and corrected during this run; the primary did not change

The first execution reported the leakage-free subset as **exactly 1.0000**,
which is not a result but an artefact. `TEST_LEAKFREE.csv` contains only
positives by construction, so masking on membership selected a set with no
negatives in it, and average precision over an all-positive set is 1.0 trivially.

Corrected: the leakage-free evaluation uses leakage-free positives **plus all
test negatives**, which is sound because test negatives never appear in training
(verified: zero overlap between the 100,000 test and 420,000 CV negatives).

**The primary endpoint is bit-identical across the two executions** — 0.7550853665193707
both times, with identical per-unit values. The correction touched only the
sensitivity mask. The primary was not recomputed in search of a better number
and could not have been; the first run's record is retained in the scratch
history and the equality was checked rather than asserted.

Had the artefact gone unnoticed it would have been the most flattering possible
reading — a perfect score on the subset specifically meant to show the result
was not memorisation.

## What this does NOT yet establish

**The cross-platform transfer analysis has not been run.** G5 measured the
acquisition instrument as separable from peptide sequence alone at AUROC 0.645
against a 0.515 control, and no split over these participants can separate
platform from participant. The pre-committed interpretation (REPORT.md,
Discussion) is explicit: a result that rejects but collapses across platforms
means the signal is substantially instrument rather than presentation.

**Until that analysis runs, this number is not attributable to presentation
biology.** The allele-disjoint analysis (D001) is likewise outstanding.

Both were preregistered before any result existed, and both require their own
training runs.
