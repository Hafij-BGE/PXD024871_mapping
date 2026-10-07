# QC G12 (part) — Dominant-allele-held-out transfer · D001, D029, D030

**Run:** 2026-10-07 · `scripts/train_cnn.py --mode allele`, then
`scripts/allele_leakfree.py` · CPU, torch 2.14.1
**Artifacts:** `results/model/allele.json` (as run),
`allele_leakfree.json` (corrected), `allele_neutral.json`,
`allele.log`, `allele_leakfree.log`, 15 checkpoints `allele_*_s*.pt`
**Configuration:** `{E:16, C:32, k:3, p:0.0}` from `selection.json`, not re-tuned
**Replicates:** 5 seeds per arm from `seed('allele_init', ·)`; per-unit AP is the
mean across the 5 models (D027)

**Status: COMPLETE, VERDICT INCONCLUSIVE.** The preregistered sign test does not
support an allele effect. Its premise is measurably false, which is recorded but
does not convert the result into a pass. **G13 stays held.** G12 as a whole is
not passed — §18 remains blocked by D006.

---

## 1. The headline: holding out the dominant allele costs nothing visible

P_AD is D001 run verbatim — train on the non-carriers of HLA-A\*02:01, test on
the 29 carriers. 18 of the 23 train, 5 are the early-stopping holdout (D029).

| P_AD, 29 carriers | mean per-unit AP | CI99 | own floor | lift |
|---|---|---|---|---|
| all rows | 0.7422 | [0.7302, 0.7534] | 0.6371 | +0.1051 |
| leakage-free against its own 18 training units | 0.7210 | [0.7103, 0.7308] | 0.6147 | +0.1064 |

The lift is +0.106, against +0.102 and +0.104 for the two cross-platform arms
(R10) — indistinguishable. **A model that has never seen a unit carrying the
most common class-I allele in this cohort performs on carriers of it exactly as
well as it does anywhere else.**

Read with D029's measurement, that is weaker than it sounds. Only 5 of the 29
test units' 36 alleles are absent from training; 23 of 29 units have exactly
one unseen allele; the mean unseen fraction is 21.7%. Four fifths of each test
unit's repertoire comes from alleles the model has seen, so a real effect
arrives attenuated roughly fivefold and this arm has little power to see it.

## 2. The matched contrasts, corrected for memorisation

### 2.1 The stratum as D029 defined it was invalid, and this is why

D029 defined the allele-enriched stratum as sequences observed in ≥2 of the 15
**C_pool** units and none of the 15 **N_pool** units. C_pool is M_AM's training
pool and N_pool is M_AD's. So the definition guaranteed the outcome:

| | share of stratum rows in the held-out carriers |
|---|---|
| sequences M_AM trained on | **97.93%** |
| sequences M_AD trained on | **0.00%** |

M_AM had memorised almost every sequence in the set; M_AD provably could not
have seen one. The +0.0660 that definition produced in `allele.json` is a
memorisation measurement wearing an allele label. **It is not reported as a
result.** `allele.json` is kept as run — D030 records the flaw rather than
deleting the number.

This is the second instance of the same failure in this project: the first
`TEST_LEAKFREE` mask selected a set containing no negatives and returned a
perfect 1.0000. Both times a subset was defined by a property that fixed the
answer. The check that catches it is to measure, for every evaluation subset,
what each arm had already seen.

### 2.2 The corrected row sets

Every row set below **excludes any positive either matched arm saw in
training**, so the two models are equally naive to every sequence scored.
Carrier-linkage is then expressed the only way that survives: recurrence among
**held-out** carriers plus absence from every non-carrier. A
recurrence-matched control is scored alongside — equally recurrent, equally
unseen, but *not* exclusive to one allele class.

| Contrast I — 14 held-out carriers | matched (M_AM) | mismatched (M_AD) | paired difference | CI99 | units positive |
|---|---|---|---|---|---|
| leak-free, all rows | 0.7002 | 0.6930 | +0.0072 | [−0.0015, +0.0162] | 9 / 14 |
| leak-free carrier-**exclusive** stratum | 0.8075 | 0.7740 | **+0.0335** | **[+0.0236, +0.0438]** | **14 / 14** |
| leak-free recurrence-matched control | 0.8451 | 0.8394 | +0.0056 | [−0.0137, +0.0279] | 8 / 14 |

| Contrast II — 8 held-out non-carriers | matched (M_AD) | mismatched (M_AM) | paired difference | CI99 | units positive |
|---|---|---|---|---|---|
| leak-free, all rows | 0.7115 | 0.7115 | +0.0000 | [−0.0051, +0.0078] | 3 / 8 |
| leak-free non-carrier-exclusive stratum | 0.8030 | 0.8161 | **−0.0131** | [−0.0287, +0.0040] | 2 / 8 |
| leak-free recurrence-matched control | 0.8367 | 0.8302 | +0.0065 | [−0.0296, +0.0507] | 3 / 8 |

### 2.3 What the carrier-exclusive effect is not

Three competing explanations for the +0.0335, each excluded by measurement
rather than by argument:

| Explanation | Test | Result |
|---|---|---|
| Memorisation | every scored sequence absent from both training sets | 0% leakage by construction of the row set |
| Recurrence, not allele class | paired difference-of-differences, exclusive stratum vs recurrence-matched control, same 14 units | **+0.0279, CI99 [+0.0067, +0.0472], 12/14 positive** |
| M_AM is simply the better training set | **direct** estimate on class-shared peptides (seen in both classes, unseen by both arms), 22 held-out units, neither arm matched | **δ = +0.0005, CI99 [−0.0081, +0.0092], 11/22** — no quality difference exists |

The nuisance parameter is zero, and its interval excludes the +0.0335 by a wide
margin. The effect is specific to carrier-exclusivity and not to recurrence.

## 3. The preregistered verdict, and why it is still inconclusive

D029 fixed the reading before the run: **both contrasts positive** is an allele
effect; **opposite signs** mean one training set is simply better and contrast I
alone would have been misread.

**The signs are opposite.** Contrast I is +0.0335 on its exclusive stratum;
contrast II is −0.0131 on its own. By the rule as written, **this result does
not support an allele effect.**

The rule's premise is nonetheless false here: §2.3 measures the training-set
quality difference the rule was proxying for and finds it to be +0.0005. There
are no opposite signs *for the stated reason*, because the stated cause does not
exist in this data.

**That observation is post-hoc and does not convert a failed preregistered test
into a passed one.** What it establishes is that the rule misclassifies this
result, not that the allele interpretation is correct.

**What D029 got wrong, and it was knowable in advance.** The rule assumed the
two groups are symmetric. They are not. The 29 carriers all share
HLA-A\*02:01. The 23 non-carriers share only its *absence* and span **41
alleles** — a figure that is in D029's own table. "Non-carrier-exclusive"
peptides are therefore not restricted by any shared allele; they are peptides
missing from the carrier group for mixed reasons, and nothing predicts that a
non-carrier-trained model should learn them better. Contrast II is a weak
replication test by construction, not a failed one. This should have been seen
when the rule was written.

**Status: suggestive, not established.** There is a real, unanimous effect on
carrier-exclusive peptides that is not memorisation, not recurrence and not
training-set quality. The preregistered confirmation test is uninformative by
construction, and no post-hoc reasoning substitutes for it.

## 4. The test that would settle it

**Repeat the entire design with a different common allele.** HLA-C\*07:02 is in
24 of 52 units and HLA-A\*01:01 in 17, so both support the same 12-unit matched
arms. If each allele's own carriers show the exclusive-stratum effect for
*their* allele, the effect is allele-specific. If the same arm wins regardless
of which allele defines the split, it is not. Unlike contrast II, this test is
symmetric by construction, because each split's carrier group shares the allele
that defines it.

Not run here. Adding arms after seeing a preregistered test fail is how a
negative result gets converted into a positive one, so this is named as the
follow-up and left for a decision rather than run in the same breath.

## 5. What this does and does not establish

**Establishes.** Performance does not degrade when the cohort's most common
class-I allele is absent from training (§1), at this design's sensitivity.
Holding out that allele costs +0.0072 of a +0.106 lift at the whole-repertoire
level, with an interval containing zero.

**Suggests.** Sequence features specific to peptides exclusive to carriers of
that allele are learnable from carriers and not from non-carriers (+0.0335,
14/14 units, all three alternatives excluded).

**Does not establish.** Allele-specific binding. Carrier-linked is not
A\*02:01-restricted: the stratum also captures peptides restricted by alleles in
linkage with A\*02:01, and any other systematic difference between the two
groups. Nothing here is allele deconvolution, and the one preregistered test
designed to confirm the effect cannot.

**G13 stays held.** §20 must not be written as biology on this. The analysis
D025 and D001 were meant to jointly license it have now both run: the signal
survives an unseen instrument (R10) and an unseen dominant allele (§1), which
rules out two specific confounds and licenses neither a presentation claim nor
an allele-specificity claim.

## 6. Limitations

1. **Contrast II has 8 units** and is structurally weak (§3). Its magnitude is
   not determined and its sign should not be read as evidence either way.
2. **The exclusive strata are selected on held-out observation data** —
   recurrence among the test units themselves. Both arms are scored on identical
   rows so the pairing is valid, but the absolute AP on these strata (0.77–0.87)
   is not comparable to R9's: set size, prevalence and peptide difficulty all
   differ.
3. **All three arms train on units inside the primary test partition**, as the
   transfer arms did. These models serve this analysis only and never §25.
4. **§2.3's neutral estimate and §2.2's corrected row sets are post-hoc**, built
   after the invalid stratum was found. They correct an error; they are not a
   preregistered analysis.
5. **One allele, one cohort.** A\*02:01 is the only allele tested, and §4 is why
   that matters.

## 7. Reproduction

```
python3 scripts/train_cnn.py --mode allele      # 3 arms x 5 seeds
python3 scripts/allele_leakfree.py              # corrected row sets, no retraining
```

Both refuse to run without `selection.json` and `endpoint.json`. Pools from
`seed('allele_split')`, early-stopping holdouts from `seed('allele_valsplit')`,
weights from `seed('allele_init', i)`, intervals from `seed('allele_bootstrap')`
and `seed('allele_leakfree_bootstrap')`, stratum negatives from
`seed('allele_stratum_negatives')` and `seed('allele_leakfree_negatives')`, the
neutral estimate from `seed('allele_neutral_*')`, the
difference-of-differences from `seed('allele_dod')`. One 2-epoch single-seed
plumbing test was run on M_AM beforehand under the shortened-run namespace and
discarded as a test.
