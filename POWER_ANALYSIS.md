# POWER AND RESOLUTION ANALYSIS

**Run:** run-001, 2026-10-06 · **Code:** `scripts/power_analysis.py` ·
**Outputs:** `results/power/power_grid.csv`, `results/power/power_params.json`
**Status:** RESOLVED as an analysis; the decisions it informs (D007, D008) remain OPEN.

## Question

Proposal §16 makes the participant the resampling unit and §25 claims
generalization to unseen participants. Uncertainty on that claim is bounded by
the number of held-out participants and by how much performance varies between
them. This quantifies the bound, so D007 (minimum-N) and D008 (decision rule)
can be set against numbers instead of intuition.

## Model and what is assumed

Binormal score model: participant *i* has latent discrimination
*d_i* ~ N(*d̄*, *τ*²); positives score N(*d_i*, 1), negatives N(0, 1). Estimand
is the **mean per-participant average precision** — the participant-level
quantity §17 asks for. Uncertainty by cluster bootstrap resampling participants.

Three things are assumed, not derived:

- ***τ*, the between-participant SD of discrimination, is unknown and
  unmeasurable before data exist.** It is swept at 0.10 / 0.25 / 0.50 rather
  than assumed, and it turns out to be the dominant term (F5). Every number
  here is conditional on it.
- **Per-participant peptide counts are a reconstruction** of the described
  acquisition-count marginals, not observed data. Recorded as such in
  `power_params.json`; to be replaced after S1/S2 retrieval.
- **The binormal model is a convenience.** Real score distributions are not
  Gaussian. It is the standard ROC-analysis model and is adequate for sizing,
  but it is not a prediction.

Estimators were cross-validated rather than trusted: analytic AP returns
prevalence exactly at zero discrimination for three prevalences, agrees with
the empirical estimate to three decimals, and is insensitive to integration
grid (4 decimals between 8001 and 24001 points).

---

## Findings

### F1 — The §25 hypothesis as written is close to unfalsifiable

Power to reject "no better than prevalence" is **1.00 in every one of the 54
main-grid cells**, and remains 1.00 down to a mean per-participant AUROC of
**0.60** — a nearly useless classifier.

| mean AUROC | estimand AP | lift over prevalence | half-width | power |
|---|---|---|---|---|
| 0.60 | 0.1351 | +0.0442 | 0.0240 | 1.00 |
| 0.70 | 0.2093 | +0.1184 | 0.0371 | 1.00 |
| 0.80 | 0.3441 | +0.2532 | 0.0545 | 1.00 |
| 0.90 | 0.5759 | +0.4850 | 0.0574 | 1.00 |

*(K=10, τ=0.25, 1:10)*

"Better than chance" will essentially always be declared. Passing §25 as
currently worded would therefore carry almost no information. **D008 must
specify a lift, not a direction.**

### F2 — Resolution is set by participant count; B is irrelevant

Mean CI half-width against bootstrap replicates (τ=0.25, 1:10):

| | B=200 | B=1,000 | B=2,000 | B=10,000 | B=50,000 |
|---|---|---|---|---|---|
| K=10 | 0.0519 | 0.0527 | 0.0527 | 0.0536 | 0.0523 |
| K=26 | 0.0339 | 0.0344 | 0.0344 | 0.0348 | 0.0353 |

A 250-fold increase in B moves the half-width by less than 0.002 — pure Monte
Carlo noise. Going from K=10 to K=26 cuts it by **35%**. §16's B=10,000 is
harmless but it is not the precision lever, and the proposal should stop
implying otherwise.

### F3 — Nominal 95% intervals do not deliver 95% coverage

Empirical coverage of the asymptotic estimand by nominal-95% percentile
cluster-bootstrap intervals:

| K | 1:1 | 1:10 | 1:100 |
|---|---|---|---|
| 5 | 0.79–0.83 | 0.78–0.83 | 0.75–0.84 |
| 10 | 0.88–0.92 | 0.88–0.89 | 0.80–0.92 |
| 16 | 0.90–0.94 | 0.90–0.94 | 0.73–0.91 |
| 26 | 0.88–0.95 | 0.88–0.93 | 0.66–0.94 |

*(range across τ = 0.10 / 0.25 / 0.50)*

At K=5 a "95%" interval is really an ~80% interval. Coverage approaches nominal
only at K≥16, and not at the extreme class ratio. Any interval reported from
this design should be labelled approximate, with the coverage shortfall stated.

### F4 — At extreme class ratio the estimator itself is biased, and the bias dominates

Empirical AP is biased **upward** relative to the asymptotic value. The bias is
small in absolute terms but large relative to the interval:

| class ratio | bias (K=26) | |bias| ÷ half-width, τ=0.10 |
|---|---|---|
| 1:1 | +0.0024 | 0.18 |
| 1:10 | +0.0058 | 0.31 |
| 1:100 | +0.0061 | **0.79** |

This explains the worst coverage cell in F3 (1:100, τ=0.10, K=26 → 0.66): the
interval is narrow and correctly placed around a **biased** point estimate, so
it misses the true value. The failure is bias, not width, and widening B or K
does not fix it.

Consequence: at 1:100 the reported AUPRC is optimistic by roughly 0.006
absolute against a lift of 0.063 — about **10% relative inflation**, in the
flattering direction.

### F5 — *τ* is the dominant unknown

Half-width at K=10, 1:10: **0.028** (τ=0.10) → **0.053** (τ=0.25) → **0.095**
(τ=0.50). Roughly linear in τ, and a 5× swing across the plausible range —
larger than the effect of tripling K. Since τ cannot be known until data exist,
**the achievable precision of this study is not yet knowable**, only bounded.

### F6 — Class ratio drives relative precision

Half-width as a fraction of the lift over prevalence (τ=0.25); below 1 means
the interval is narrower than the effect:

| K | 1:1 | 1:10 | 1:100 |
|---|---|---|---|
| 5 | 0.142 | 0.254 | 0.475 |
| 10 | 0.111 | 0.210 | 0.380 |
| 26 | 0.076 | 0.136 | 0.250 |

The same underlying discrimination is estimated 3–5× less precisely, in
relative terms, at 1:100 than at 1:1. Combined with F4, extreme ratios are
doubly bad: the estimate is more inflated and less precise.

### F7 — The §18 paired comparison is far better powered than the §25 absolute claim

Power to detect a difference between two predictors scored on the same
peptides, paired cluster bootstrap (τ=0.25, 1:10, shared participant effect):

| K | ΔAP=0.015 | 0.035 | 0.070 | 0.128 | 0.200 |
|---|---|---|---|---|---|
| 5 | 0.21 | 0.49 | 0.90 | 0.99 | 1.00 |
| 10 | 0.23 | 0.58 | 0.99 | 1.00 | 1.00 |
| 16 | 0.40 | 0.85 | 1.00 | 1.00 | 1.00 |
| 26 | 0.51 | 0.95 | 1.00 | 1.00 | 1.00 |

Minimum detectable difference at 80% power: **ΔAP ≈ 0.05** at K=10,
**ΔAP ≈ 0.03** at K=26. Pairing removes the between-participant variance that
limits the absolute claim, so the comparison is the more informative analysis
at this sample size.

---

## What this means for the open decisions

**D007 — minimum-N gate: the proposal gates on the wrong variable.** It frames
the threshold in eligible positive peptides. F2 and F5 show resolution is set
by **held-out participants**, so the gate belongs in participants. Proposed:
K_test ≥ 13 for intervals worth reporting (F3), and treat K_test ≤ 8 as
exploratory regardless of peptide count. A 60/20/20 split of ~52 participants
gives K_test ≈ 10 — **marginal**. Grouped cross-validation over all participants
uses the data better but reuses participants across folds; that trade is
unresolved and belongs in D007.

**D008 — decision rule.** Replace "better than chance" with a lift threshold.
From the effect sweep, differences of ~0.10 AP are cleanly resolvable at K=10
and ~0.04 is marginal. Proposed: require the CI lower bound to exceed
prevalence + 0.10 at 1:10, and report the coverage shortfall from F3 alongside.

**D002 — negative strategy and class ratio.** F4 and F6 argue against 1:100 on
statistical grounds independent of the composition argument: it inflates the
point estimate and degrades relative precision. 1:1 or 1:10 is preferable.

**§16 — bootstrap.** Keep B=10,000 (harmless), stop presenting it as precision.
Consider BCa or studentized intervals to address F3, and a bias correction for
F4 if an extreme ratio is chosen anyway.

**New: D014 — should §18 be the primary endpoint?** F7 shows the paired
comparison is better powered than the absolute claim at every K. Proposing,
not making, this change: it would make the confirmatory question "does the CNN
differ from existing predictors on identical rows" rather than "is the CNN
better than chance", which is both more informative and better matched to the
design's resolution. Recorded as a decision rather than applied.

## Feasibility verdict

The design is **not underpowered for a coarse claim and not adequate for a fine
one.** It can resolve "substantially better than prevalence" and predictor
differences of ~0.05 AP and up. It cannot resolve fine distinctions, and at
K≤8 it supports nothing confirmatory. The confirmatory arm is viable, provided
§25's threshold is raised (D008) and the gate is stated in participants (D007).

This does not clear the project to proceed — it clears the *statistical design*.
Whether enough eligible participants and peptides exist is still unknown and
still blocked on retrieval.

## Limitations of this analysis

1. τ is unknown; all precision figures are conditional on the sweep.
2. Peptide counts are a reconstruction of described marginals, not observed.
3. The binormal model is an assumption; real score distributions are not Gaussian.
4. Coverage is measured against the **asymptotic** estimand. Against the
   finite-sample expectation the shortfall in F3 would be smaller, but the F4
   bias would then be hidden rather than removed.
5. The paired analysis assumes a participant effect shared between predictors
   (easy participants are easy for both). Weaker sharing reduces the pairing
   gain and raises the MDE in F7.
6. Simulation error: 250 replicates per cell, so powers near 0.5 carry ~±0.03
   and coverages ~±0.02. Differences smaller than that are not real.
7. No multiplicity correction. Reporting several metrics across several splits
   inflates the chance of a spurious pass; not modelled here.

## Reproduce

```
pip install numpy scipy        # versions in ENVIRONMENT.md (env-001)
python3 scripts/power_analysis.py
```

Deterministic given `SEED = 20261006`. Runtime ~4 min on 4 cores.
