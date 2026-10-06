# QC_G4 (prep) — the extracted peptide universe

All 52 class-I containers retrieved, publisher checksum verified, extracted and
deleted. run-006. This is the input to G4, not G4 itself: the gate also requires
negative construction (D002) and the frozen filtering rule (D004).

| Result | Check | Detail |
|---|---|---|
| PASS | All units extracted | 52/52 |
| PASS | Publisher checksums | 52/52 verified; 4 historical failures all retried clean |
| PASS | Length window | union is entirely 8–12; the deposited search was pre-restricted |
| PASS | Containers deleted | peak disk held; none retained |

## The number everything was waiting for

**Union: 2,658,972 unique 8–12mers** across 52 units.

| | |
|---|---|
| Sum of per-unit counts | 3,850,275 |
| Redundancy factor | **1.45×** |
| Per unit | min 39,991 · median 71,784 · max 198,567 |
| Length mode | 9-mers, 27.8% |
| Confidence level 1 | 99.29% |

## My projection was 42% low

Fitted on the first five units, Heaps' β = 0.840 projected **1,547,364**. The
actual is **2,658,972** — an error of **−41.8%**. β over all 52 units is 0.977,
far closer to linear than five units suggested, and the last unit added was
still **55% novel**. Accumulation had not begun to saturate anywhere in the
range I extrapolated from, so a five-point fit was never going to capture it.

Recorded because the projection drove two decisions — D007's feasibility call
and §14's sizing — and an estimate that is never checked against the outcome
teaches nothing. The direction matters too: I under-estimated, so the compute
budget built on it was optimistic rather than conservative.

## Sharing between units is low, and that settles D003

| Observed in | Sequences | Share |
|---|---|---|
| exactly 1 unit | 2,124,276 | **79.9%** |
| 2 units | 314,952 | 11.8% |
| 3+ units | 219,744 | 8.3% |

**Four fifths of the universe is private to a single participant.** The
cross-split leakage I raised in D003 — arguing that ligandomes overlap heavily
between participants sharing alleles — was wrong in the reassuring direction.
The exposure is **534,696 sequences** that appear in more than one unit, which
is a concrete number for the split rule rather than the serious hazard I
described.

It also sharpens the sampling-depth question in §14. At 1.45× redundancy with
the last unit still 55% novel, these repertoires are nowhere near exhaustively
sampled, so low overlap remains consistent with deep undersampling of a far
larger presented space rather than with genuinely disjoint biology.

## D004 is confirmed a no-op

99.29% of the union is at the highest confidence level. Re-filtering removes
0.7%. Whatever purity control D004 settles on, `ConfidenceLevel` is not it; the
decision must be re-framed around the `PeptideScores` table.

## D007 clears, overwhelmingly

2.66M eligible positives against any plausible minimum-N threshold. The
confirmatory arm is not data-limited.

## But §14 is breached again

At the measured union, a 100-run grid costs **120 h at 1:1** and **662 h at
1:10**, against a 96 h cap. The budget has now been wrong twice in the same
direction, both times because it was sized on an estimate of the dataset rather
than the dataset.

**The resolution is not a bigger budget.** run-001 established that uncertainty
is bounded by the number of held-out units — 52 — and not by peptide count.
Positives beyond what makes each unit's average precision stable buy almost
nothing statistically while costing linearly in compute:

| Per-unit cap | Total positives | Grid at 1:1 |
|---|---|---|
| 5,000 | 260,000 | 11.8 h |
| 10,000 | 520,000 | 23.6 h |
| 20,000 | 1,040,000 | 47.1 h |
| 40,000 | 2,080,000 | 94.2 h |

A per-unit cap is therefore a **design decision justified by the power
analysis**, not a budget cut — which is the distinction §14 insists on, since
the reduction ladder exists to avoid trading away design to afford compute.
Opened as D024; it must close before the split is locked, and it must be
preregistered rather than chosen once results are visible.
