# QC G11 — Predictor comparison · §18, D006, D033

**Run:** 2026-10-07 · `predictor_contamination.py`, `predict_mhcflurry.py`,
`compare_predictors.py` · CPU
**Artifacts:** `results/qc/predictor_contamination.json`,
`predictor_comparison.json`, `predictor_task_mismatch.json`,
`results/predictors/comparison_with_predictors.csv`,
`mhcflurry_2_0_0_test_scores.csv`, `mhcflurry_2_3_0_test_scores.csv`,
`data/raw/S6/provenance.jsonl`
**Nothing was retrained.** The CNN is the frozen 25-model final fit (D027); the
predictors are released artifacts registered as S6 sources with sha256.

**Status: PASSED.** Both predictors admitted under D006 as quantified
`OVERLAPPING`. The CNN outperforms both on identical rows under the strictest
subsetting, unanimously across participants. **§18 is not promoted** (D014), and
**the comparison is not a fair test of predictor quality** — §4 says why, with
numbers.

---

## 1. Admission under D006

D006: *"No predictor enters the §18 comparison until its training peptide list
has been retrieved and registered as an S6 source, with checksum and version."*

Four artifacts retrieved and registered in `data/raw/S6/provenance.jsonl`:

| Artifact | bytes | sha256 (first 16) |
|---|---|---|
| `models_class1_presentation.20200611.tar.bz2` | 135,359,558 | `6193efee43e768c6` |
| `data_curated.20200427.tar.bz2` | 73,435,569 | `5ec61817b85ef5fa` |
| `models_class1_presentation.20260928.tar.bz2` | 160,356,140 | `768e360832b3d45d` |
| `data_curated.20231023.tar.bz2` | 77,540,318 | `784dc4c9769d4c0e` |

**The authoritative training list is the one each model bundle ships**, not the
curated release the line declares — see D033. Release 2.3.0 pairs 2026-09-28
models with a 2023-10-23 curated file, so the declared file would only have
bounded the overlap below.

### M7 contamination, exact sequence match (D016 — nothing fuzzy)

| | MHCflurry 2.0.0 | MHCflurry 2.3.0 |
|---|---|---|
| training peptides (union over components) | 605,189 | 666,025 |
| overlap with test **positives** | 8,093 — **8.29%** | 8,893 — **9.11%** |
| overlap with test **negatives** | 1,199 — **1.20%** | 1,157 — **1.16%** |
| positive : negative bias | **6.9 : 1** | **7.9 : 1** |
| per-unit positive overlap | 4.89–15.42% | 5.22–17.88% |
| **verdict** | **`OVERLAPPING`, quantified** | **`OVERLAPPING`, quantified** |

**D006's two predictions both hold.** The overlap is biased 7:1 toward
positives, so contamination hands the predictor peptides it was fit on and
almost none of the decoys it must reject — it moves the comparison *against* the
CNN. And provenance is indeed no substitute: the 2.0.0 models predate this
deposit's 2021-09 publication by fifteen months and name it nowhere, yet
**8.29% of this test partition's positives are in their training data anyway**,
arriving through other studies. On a date argument that line would have been
called `CLEAN`.

## 2. The comparison

Three row sets (D033). The primary is naive to **both** systems: removing only
the predictor's 8–9% while leaving the CNN's measured 15.99% (D003) would hand
the CNN a selectively easier dataset, which §18 forbids in those words.

### 2.1 Primary — mutually naive · 175,524 rows, prevalence 0.440

| System | units | mean per-unit AP | CI99 | per-unit range |
|---|---|---|---|---|
| **CNN** | 10 | **0.6859** | [0.6703, 0.7019] | 0.6578–0.7158 |
| MHCflurry 2.0.0 | 10 | 0.5481 | [0.5342, 0.5646] | 0.5188–0.5880 |
| MHCflurry 2.3.0 | 10 | 0.5519 | [0.5382, 0.5688] | 0.5303–0.5959 |

| Contrast | difference | CI99 | units |
|---|---|---|---|
| CNN − MHCflurry 2.0.0 | **+0.1378** | [+0.1151, +0.1583] | **10 / 10** |
| CNN − MHCflurry 2.3.0 | **+0.1340** | [+0.1126, +0.1505] | **10 / 10** |

A random ranker scores AP ≈ prevalence = 0.440 here. So the CNN is +0.25 above
random and MHCflurry +0.11.

### 2.2 The other two row sets

| Row set | rows | prevalence | CNN | MF 2.0.0 | MF 2.3.0 | CNN − 2.0.0 | CNN − 2.3.0 |
|---|---|---|---|---|---|---|---|
| mutually naive (primary) | 175,524 | 0.440 | 0.6859 | 0.5481 | 0.5519 | +0.1378 | +0.1340 |
| predictor-naive only (D006 literal) | 187,764 | 0.477 | 0.7285 | 0.5892 | 0.5938 | +0.1393 | +0.1347 |
| full partition (D006 secondary) | 199,978 | 0.500 | 0.7551 | 0.6629 | 0.6673 | +0.0922 | +0.0877 |

**The CNN's advantage is largest where contamination is smallest**, which is the
direction that matters: it is not produced by either system's memorisation. On
the full partition the gap narrows to +0.09 because MHCflurry gains more from
its overlap (0.552 → 0.663) than the CNN does from its own (0.686 → 0.755).

**Absolute AP is not comparable across these three rows of the table**, because
average precision depends on prevalence and the subsetting changes it from 0.440
to 0.500. Within each row set the systems are on identical rows and the paired
contrast is exact.

The full-partition CNN value reproduces the endpoint at **0.7551**, which is the
check that this pipeline scores the same rows the same way.

## 3. What this establishes

For the task this dataset defines — distinguishing peptides observed in a
participant's ligandome from unobserved peptides drawn from the same source
proteins — **a small CNN trained on 42 participants of this cohort outperforms
an off-the-shelf presentation predictor by about 0.134 average precision, on
rows neither system has seen, in every one of 10 held-out participants.**

## 4. Why this is not a fair test of predictor quality

**§18's own Limitations field anticipated this**: *"Existing predictors designed
for different tasks (binding affinity vs. presence/absence)."* It can now be
quantified rather than asserted.

**MHCflurry is being asked the wrong question.** It predicts whether a peptide
*can be presented*. Our label records whether a peptide *was observed*. Set-C
negatives are peptides from the same source proteins that were never detected —
and many of them are perfectly plausible binders:

| MHCflurry 2.3.0 call | positives | **negatives** |
|---|---|---|
| presentation percentile ≤ 0.5 | 16.41% | 3.90% |
| presentation percentile ≤ 2.0 | 30.05% | **11.78%** |
| predicted affinity ≤ 500 nM | 26.07% | **9.11%** |
| predicted affinity ≤ 50 nM | 10.67% | 1.56% |

**11,778 of 100,000 set-C negatives are ranked as strong presenters.** Every one
is a peptide our labels call negative because it went unobserved and the
predictor calls presentable. Those are counted as the predictor's errors. Some
of them are the predictor being right and the label being a detection artefact.

**The CNN also has an advantage that has nothing to do with modelling
presentation.** It was trained on 42 participants from this cohort — same
laboratory, same two instruments, same protocol, same negative construction. R10
measured the instrument component of that at 0.04–0.06 AP. MHCflurry has never
seen this cohort. A model trained on the task, distribution and technical
artefacts of the test set beating a model that was not is close to tautological,
and the margin here should be read as the value of task-specific training rather
than as a verdict on either architecture.

**So the defensible reading is narrow:** the CNN adds information over an
off-the-shelf predictor *for this task on this cohort*. §18 does not establish
that the CNN is a better model of HLA class-I presentation, and nothing here
should be cited as if it did.

## 5. Not promoted

D014 made §18's promotion to primary conditional on every admitted predictor
being `CLEAN` or quantified `OVERLAPPING`. **That condition is now met** — and
D014 equally states that a switch after seeing results is endpoint switching
regardless. §25 was read, closed and reported before any predictor score
existed. §18 stays secondary. It is worth saying plainly that this document
could have argued for promotion and does not.

`UNVERIFIABLE` went unused, so D006's one-direction rule — the only circumstance
in which an unverifiable comparison may be reported as evidence — was never
invoked.

## 6. Limitations

1. **MHCflurry only.** NetMHCpan 4.1 is behind a per-user academic licence form
   at the DTU host, not scriptable, and accepting a licence on the owner's
   behalf is not mine to do. MixMHCpred is distributed through
   `raw.githubusercontent.com`, which returns 404 through this proxy even though
   release assets return 200. Both are absent and neither is reported. §18's
   input list named "NetMHCpan, MixMHCpred, or others"; this is "others".
2. **The task mismatch in §4 is the dominant limitation**, larger than anything
   the subsetting corrects.
3. **22 rows carry ambiguity codes** (X, B = Asx, Z = Glx) and are excluded from
   both systems, so the rows stay identical. MHCflurry refuses them; the CNN's
   encoder silently maps an unknown character to the pad token, so those
   peptides were encoded with internal pads. 181 such rows exist in the frozen
   positives (0.035%), 22 of them in the test partition (0.011% of its rows), so
   the effect on the endpoint is immaterial — but the encoder's silent fallback
   is a real defect and the selftest does not cover it.
4. **Partially typed units are scored on recorded alleles only** (D012 imputes
   none). Four of the ten test units have fewer than six. A missing allele can
   only lose the predictor a true positive, so this understates MHCflurry.
5. **Prevalence differs across row sets** (0.440 / 0.477 / 0.500), so absolute
   AP is comparable only within a row set.
6. **One cohort, one disease, one laboratory**, unchanged.

## 7. Reproduction

```
python3 scripts/predictor_contamination.py <extract-root>     # M7, before any score
<venv>/bin/python scripts/predict_mhcflurry.py --models <dir> --line 2.3.0
<venv>/bin/python scripts/predict_mhcflurry.py --models <dir> --line 2.0.0
python3 scripts/compare_predictors.py                          # the comparison
```
`seed('predictor_bootstrap')` for every interval. The venv carries MHCflurry and
TensorFlow; the repo environment carries torch. They are kept separate so
neither has to hold the other's dependencies, which is why scoring and comparing
are two scripts.
