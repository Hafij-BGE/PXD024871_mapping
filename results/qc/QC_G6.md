# QC_G6 — split frozen

run-011. Built by `scripts/build_split.py` from the preregistered decisions.
Frozen in `data/derived/SPLIT_FREEZE.json`.

| Result | Check | Detail |
|---|---|---|
| PASS | Participant-disjoint | no unit appears in two partitions (D011) |
| PASS | Platform-stratified | test 5 LTQ / 5 Lumos; every fold 4 LTQ / 4–5 Lumos (D025) |
| PASS | Test partition isolated | 10 units held out, untouched during model selection (§10) |
| PASS | Folds | 5, over the remaining 42 units (§14) |
| PASS | Allele-disjoint secondary constructed | 29 test / 23 train (D001) |
| PASS | Cross-platform secondary defined | 25 LTQ / 27 Lumos, both directions (D025) |
| PASS | Leakage-free subset written | 84,012 of 100,000 test rows (D003) |
| PASS | Seed derived, not reused | `seed('split')` = 3708237009 (D010) |

## Primary split

| Partition | Units | LTQ | Lumos |
|---|---|---|---|
| test | 10 | 5 | 5 |
| cv fold 0 | 9 | 4 | 5 |
| cv fold 1 | 9 | 4 | 5 |
| cv fold 2 | 8 | 4 | 4 |
| cv fold 3 | 8 | 4 | 4 |
| cv fold 4 | 8 | 4 | 4 |

Platform balance is as close as 25/27 permits in every partition, which is what
D025 requires: it does not remove the confound, it stops the split from becoming
one.

## This draw is leakier than average, and it stands

**15.99%** of test positives also appear in training. The G5 audit over 2,000
random splits found a mean of 14.59% and a range of 11.76–17.25%, so this draw
sits near the top of that range.

**It is not re-drawn.** The seed was fixed in advance (D010), and re-drawing to
obtain a less leaky split would be split shopping — the same failure as seed
shopping, and no more defensible for being motivated by a number that looks
unfavourable. A split chosen because its leakage reads better is a split
selected on a property of the data, and the preregistration exists to prevent
exactly that.

The consequence is handled rather than avoided: **84,012 leakage-free test rows**
are written to `TEST_LEAKFREE.csv`, and the D003 sensitivity analysis reports
the primary metric on both. The gap between them is the inflation, measured on
this split rather than assumed from the average.

## Secondary splits, fixed before any result

**Allele-disjoint.** Hold out all 29 units carrying HLA-A\*02:01, train on the
remaining 23. This is the split that tests whether the model generalizes across
allotypes rather than across individuals who happen to share them — the question
D001 was opened to make answerable.

**Cross-platform transfer.** Train on the 25 LTQ units and evaluate on the 27
Lumos units, then the reverse. G5 measured platform as readable from composition
alone at AUROC 0.645 against a 0.515 control, so this measures the confound's
effect on performance directly instead of inferring it.

Both are preregistered now, before any model exists, because each is the kind of
analysis that gets reinterpreted as exploratory when run after a headline number
disappoints.

## What the split does not fix

No unit spans both platforms, so platform and participant remain inseparable
(D005). Stratification bounds the artefact; it does not remove it. A test result
remains a joint statement about generalizing to unseen participants and unseen
instrument conditions, and §25 must be worded accordingly.
