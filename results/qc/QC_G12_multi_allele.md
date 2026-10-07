# QC G12 (part) — Multi-allele test · D031

**Run:** 2026-10-07 · `scripts/multi_allele.py`, then the paired
difference-of-differences · CPU, torch 2.14.1
**Artifacts:** `results/model/multi_allele.json`, `multi_allele_dod.json`,
`multi_allele.log`, 60 checkpoints `multi_*_s*.pt`
**Configuration:** `{E:16, C:32, k:3, p:0.0}` from `selection.json`, not re-tuned
**Replicates:** 5 seeds per arm; per-unit AP is the mean across them (D027).
Seed spread 0.0032–0.0105 validation AP — replicate noise is not driving
anything below.

**Status: an allele-specific effect is ESTABLISHED for HLA-A\*02:01 on a
symmetric design, replicated in direction across all five alleles, and NOT
demonstrated for HLA-C\*07:02. G13 remains HELD** — one of D031's three release
conditions fails, and the failing condition is one this design could probably
never have met. See §5.

**Memorisation check (D030's standing rule): `SEEN 0.00%` on all 21 row sets.**
Both compared arms are naive to every sequence scored, everywhere.

---

## 1. Part B — the symmetric test, which is the decisive one

Both arms are carrier-trained, each for its own allele, so neither group is the
"defined by an absence" group that made D029's contrast II uninformative. 6
training units each. `A-trained − C-trained`, paired per unit:

| Row set | raw | neutral δ | recurrence control | **adjusted** | CI99 | units |
|---|---|---|---|---|---|---|
| **A\*02:01-exclusive** | +0.0463 | −0.0013 | +0.0052 | **+0.0476** | **[+0.0314, +0.0626]** | **9 / 9** |
| **C\*07:02-exclusive** | −0.0087 | −0.0038 | −0.0088 | **−0.0049** | [−0.0366, +0.0298] | 3 / 6 |

**The sign reverses**, which is the signature D031 fixed in advance. On
A\*02:01-exclusive peptides the A\*02:01-trained model wins on every one of 9
units; on C\*07:02-exclusive peptides the C\*07:02-trained model wins, by a
small amount whose interval contains zero.

**For the A\*02:01 direction, all three alternatives are measured at zero on the
same units:** memorisation 0.00% by construction, training-set quality
−0.0013 (CI99 [−0.0182, +0.0146]), recurrence +0.0052 (CI99 [−0.0114,
+0.0250]). The adjusted effect is +0.0476 with 9 of 9 units in the same
direction. **This is the cleanest allele-specific result the dataset has
produced**, and it is the one D029 could not deliver.

**For the C\*07:02 direction, nothing is demonstrated.** The point estimate has
the predicted sign but is indistinguishable from its own recurrence control
(−0.0049 adjusted, −0.0088 control), on 6 units and the smallest stratum in the
run (542 sequences, 1,878 rows).

## 2. Part A — replication across five alleles

`carrier-trained − non-carrier-trained` on each allele's exclusive stratum, and
the same contrast adjusted by that allele's own neutral δ, paired per unit:

| Allele | carriers | test units | exclusive | neutral δ | control | **excl − δ** | CI99 | units | excl − control | CI99 |
|---|---|---|---|---|---|---|---|---|---|---|
| A\*02:01 | 29 | 19 | +0.0278 | −0.0059 | −0.0058 | **+0.0337** | **[+0.0252, +0.0421]** | **19/19** | +0.0336 | [+0.0206, +0.0473] |
| C\*07:02 | 24 | 14 | +0.0068 | −0.0091 | −0.0086 | **+0.0160** | **[+0.0048, +0.0269]** | 12/14 | +0.0155 | [+0.0031, +0.0281] |
| A\*01:01 | 17 | 7 | +0.0229 | **+0.0146** | +0.0179 | +0.0083 | [−0.0100, +0.0226] | 5/7 | +0.0050 | [−0.0096, +0.0198] |
| A\*24:02 | 16 | 6 | +0.0408 | −0.0185 | −0.0141 | **+0.0592** | **[+0.0432, +0.0732]** | **6/6** | +0.0548 | [+0.0017, +0.0972] |
| B\*07:02 | 15 | 5 | +0.0415 | +0.0091 | −0.0149 | +0.0325 | [−0.0087, +0.0722] | 4/5 | **+0.0564** | **[+0.0278, +0.0892]** |

**All five adjusted contrasts are positive.** Three of five exclude zero after
δ-adjustment; four of five exclude zero against the recurrence control. No joint
p-value is computed, per D031: the five splits draw from 52 units and most units
appear in several, so these are correlated replications, not five independent
confirmations.

### 2.1 A\*01:01 is the case the neutral estimate was built for

A\*01:01 looks like an effect until adjusted: raw +0.0229, which would have
read as confirmation. But its **neutral δ is +0.0146, CI99 [+0.0010, +0.0270]** —
for that split the carrier-trained arm really is the better model, on peptides
where neither arm is matched. Adjusted, +0.0083 with an interval containing
zero and 5 of 7 units: nothing allele-specific survives.

This is precisely the confound D029's sign rule was trying to catch by symmetry
and could not. Here it is caught by direct measurement, in one of five splits.
**Without the neutral estimate, A\*01:01 would have been counted as a fourth
replication.**

### 2.2 The two designs agree on which alleles show the effect

| Allele | Part A adjusted | Part B adjusted |
|---|---|---|
| A\*02:01 | +0.0337 | +0.0476 |
| C\*07:02 | +0.0160 | −0.0049 |

Two designs, different training sets, different test units, different
comparators — and both rank A\*02:01 above C\*07:02. C\*07:02 is the weakest
significant allele in Part A and fails in Part B. That the ordering is
reproduced is a coherence check the design did not have to pass.

**A hypothesis for why C\*07:02 is weak, offered as a hypothesis.** HLA-C is
expressed at the cell surface at substantially lower levels than HLA-A and
HLA-B, so C-restricted peptides should be a smaller share of each ligandome and
a C-exclusive stratum should carry proportionally more non-C-restricted
contamination. That is textbook immunology rather than anything this analysis
measured, it is reached after seeing the result, and the two measurements above
are of the same allele's peptides so their agreement is not independent
corroboration. It is a prediction for a cohort with more HLA-C diversity, not a
finding.

## 3. What this establishes

**Established.** A model trained on carriers of HLA-A\*02:01 ranks peptides
exclusive to A\*02:01 carriers better than a model trained on carriers of a
different allele, on held-out participants, by +0.0476 (CI99 [+0.0314,
+0.0626], 9/9 units), with memorisation, recurrence and training-set quality all
measured at zero on the same units. **The model learns genotype-linked sequence
features, and for A\*02:01 that is demonstrated allele-specifically on a
symmetric design.** Part A reproduces the direction for all five alleles tested.

**Not established.** The same for HLA-C\*07:02, or for HLA-C generally. Nor the
magnitude: +0.03 to +0.06 AP on strata that are 0.5–5% of each ligandome, which
is a detectable mechanism, not a model of presentation.

**Still not established, and this analysis does not speak to it.** That the
primary endpoint's +0.158 lift is presentation biology. The allele effect
accounts for a few hundredths of an AP point on a small subset. Everything R10
and `QC_G12_allele.md` §5 said about confounds the platforms and allele groups
*share* — source-protein abundance, detectability bias, the set-C negative
construction — stands untouched.

**Allele deconvolution is still absent.** "A\*02:01-exclusive" means exclusive
to carriers of A\*02:01, which includes peptides restricted by alleles in
linkage with it. The symmetric design rules out *the other tested allele* as the
source, which is much stronger than D029's design managed, and still not the
same as identifying the restricting allele.

## 4. Limitations

1. **Part B's C-side has 6 test units and 542 stratum sequences.** The failure
   there is as consistent with low power as with no effect, and §2.2 offers a
   third possibility.
2. **Part A's last three alleles have 7, 6 and 5 test units.** Their intervals
   are wide; A\*24:02's exclusive-minus-control interval runs [+0.0017,
   +0.0972].
3. **Correlated replication.** Most of the 52 units appear in several splits.
4. **Part B trains on 6 units, Part A on 8, D029 on 12.** Absolute AP is not
   comparable across them; only each comparison's internal contrast is.
5. **Exclusive strata are selected using held-out observation data** (recurrence
   among the test units). Both arms score identical rows so pairing is valid,
   but absolute AP on these strata (0.77–0.87) is not comparable to R9's.
6. **One cohort, one disease, one laboratory.** Unchanged.
7. **All arms train on units inside the primary test partition.** None serves
   §25, which is closed.
8. **A plumbing run previewed Part B's direction**, disclosed in D031. The
   preview's +0.0308 / −0.0189 at 2 epochs and 1 seed became +0.0463 / −0.0087
   at full budget over 5 seeds.

## 5. Why G13 stays held, and the criterion's own defect

D031 set the release condition: *"Part B showing the sign reversal, with both
directions' intervals excluding zero and both neutral estimates near zero, and
Part A's five contrasts consistent with it."*

| Condition | Result |
|---|---|
| Sign reversal in Part B | **met** (+0.0476 → −0.0049) |
| Both neutral estimates near zero | **met** (−0.0013, −0.0038) |
| **Both directions' intervals excluding zero** | **FAILS** — the C\*07:02 direction does not |
| Part A's five contrasts consistent | **met** (all five positive) |

**G13 therefore stays held.** The criterion is explicit and relaxing a criterion
in order to pass it is not available.

**The failing condition was probably unattainable, and that is my error.** D031
fixed carrier tests of 9 and 6 units for Part B — the numbers are in the entry —
and then required a nominal-99% interval from the 6-unit side to exclude zero.
At the effect sizes Part A was already indicating, that was close to impossible
before the run began. It is the same family of mistake as D029's symmetry
assumption: a reading rule whose own design cannot satisfy it. What should have
been required instead is the sign reversal plus one direction significant plus
both neutral estimates at zero — which is what the data show.

**That is not a change I will make unilaterally**, because I wrote the criterion
that is now failing and narrowing it is self-serving by construction. Recorded
in D032 as a proposal with the §20 wording it would license, for the project
owner to accept or refuse.

## 6. Reproduction

```
python3 scripts/multi_allele.py            # Part A then Part B, 60 fits
```
Pools from `seed('multi_split', i)`, early-stopping units from
`seed('multi_valsplit', i)`, weights from `seed('multi_init:{arm}', r)`,
intervals from `seed('multi_bootstrap')`, stratum negatives from
`seed('multi_negatives')`, the difference-of-differences from
`seed('multi_dod')`. Shortened runs write to `multi_allele.PARTIAL.json` under a
separate checkpoint namespace.
