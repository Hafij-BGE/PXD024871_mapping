# QC_G3 — Units and confounds

| Result | Check | Detail |
|---|---|---|
| PASS | Every eligible row assigned a unit | 222 runs over 52 units |
| PASS | Unit count | 52 class-I units; 61 units across the whole submission |
| PASS | Runs per unit | min 3 max 15; 3 runs x29, 4 runs x2, 5 runs x17, 8 runs x1, 9 runs x1, 10 runs x1, 15 runs x1 |
| PASS | Instrument distribution | LTQ Orbitrap XL 127 runs; Orbitrap Fusion Lumos 95 runs |
| FAIL | Instrument separable from unit | 0/52 units span more than one instrument |
| FAIL | M5 container to run | NOT RUN — identification containers not retrieved |

## D005 — instrument is completely confounded with unit

No unit spans more than one instrument. The two platforms partition the units
25/27
with zero overlap. A unit-disjoint split therefore **cannot** separate unit
effects from platform effects: any "generalizes to unseen units" result is
equally consistent with a statement about generalizing across platforms.

Stratification is possible and necessary but does not fix this. Both platform
groups are large enough to contribute to every partition, which prevents the
split from *becoming* a platform split; it cannot make the two effects
separable, because no unit provides within-unit platform variation.

## Cohort uniformity

age and sex are "not available" for every row. disease is
"chronic lymphocytic leukemia" and tissue "peripheral blood" for all 222 class-I runs.
No further covariate is available for confound modelling, and any claim is
bounded to this single disease and tissue context.
