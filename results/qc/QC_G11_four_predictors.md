# QC G11 (revised) — §18 across four predictors · D006, D033, D035, D036

**Run:** 2026-10-07 · `contamination_all.py`, `predict_netmhcpan.py`,
`predict_mixmhcpred.py`, `compare_predictors_all.py`
**Supersedes** `QC_G11.md`, which covered the two MHCflurry lines. That document
is kept as written; nothing in it is retracted except the "not obtained" rows in
its §6, corrected below.
**Nothing was retrained.** The CNN is the frozen 25-model final fit (D027).

**Status: PASSED.** Four predictors admitted as quantified `OVERLAPPING`. The
CNN leads all four by 0.137–0.142 average precision on rows no system has seen,
in every one of 10 participants. **The four predictors agree with each other to
within 0.0046, which is the finding that most constrains how the lead should be
read.**

---

## 1. What changed since QC_G11

QC_G11 §6 recorded NetMHCpan and MixMHCpred as not obtained. **Both reasons were
wrong**, and D036 records the pattern:

| Recorded | Actually |
|---|---|
| NetMHCpan: licence form, not scriptable | The **software** is licence-gated; the **training data** D006 needs is open supplementary material. The owner obtained the licence on 2026-10-07 |
| MixMHCpred: `raw.githubusercontent.com` refused by the proxy | That host returns 200 on any real file path. The bare host had been tested and the result generalised. The repository clones normally |

Both errors took the same shape — probing the cheapest URL and generalising a
negative — and it is the same shape as D033's claim about github.com. The fix
recorded in D036 is a habit: **probe the specific artifact, never the host.**

## 2. Admission under D006 — one method, all five

`contamination_all.py` supersedes the MHCflurry-only script and adds the split
the earlier one lacked: overlap counted separately for peptides the predictor
saw as positive and as negative.

| Predictor | train pos | train neg | our positives seen | our negatives seen | bias | verdict |
|---|---|---|---|---|---|---|
| MHCflurry 2.0.0 | 556,234 | 50,315 | 8.29% | 1.20% | 6.9 : 1 | `OVERLAPPING` |
| MHCflurry 2.3.0 | 514,286 | 181,294 | 9.11% | 1.16% | 7.9 : 1 | `OVERLAPPING` |
| NetMHCpan 4.1 | 387,475 | 11,693,931 | 9.22% | 3.32% | 2.8 : 1 | `OVERLAPPING` |
| **NetMHCpan 4.2** | 440,390 | 12,741,099 | **20.74%** | **16.20%** | **1.3 : 1** | `OVERLAPPING`, **not scored** |
| MixMHCpred 3.0 | 354,675 | 2,018,404 | 10.36% | 3.33% | 3.1 : 1 | `OVERLAPPING` |

`UNVERIFIABLE` went unused. D006's one-direction rule was never invoked.

**NetMHCpan 4.2 is in this table and in no comparison**, because its software
needs a licence separate from the 4.1 grant. Were it scored, D006's asymmetry
argument would not protect it: at 1.3:1 it has been trained to reject one sixth
of our decoys, which is help rather than handicap.

## 3. The comparison

D036 fixed two row sets, because extending D033's mutually-naive rule to all
four would have deleted 17.2% of rows from every contrast to accommodate the
most contaminated predictor.

### 3.1 Common row set — 165,574 rows, prevalence 0.440 · every system naive

| System | mean per-unit AP | CI99 | vs CNN | CI99 | units |
|---|---|---|---|---|---|
| **CNN** | **0.6852** | [0.6682, 0.7027] | — | — | — |
| MHCflurry 2.3.0 | 0.5479 | [0.5329, 0.5652] | **+0.1373** | [+0.1163, +0.1519] | **10 / 10** |
| NetMHCpan 4.1 | 0.5472 | [0.5302, 0.5721] | **+0.1380** | [+0.1068, +0.1634] | **10 / 10** |
| MHCflurry 2.0.0 | 0.5443 | [0.5306, 0.5609] | **+0.1409** | [+0.1189, +0.1605] | **10 / 10** |
| MixMHCpred 3.0 | 0.5434 | [0.5290, 0.5599] | **+0.1418** | [+0.1175, +0.1631] | **10 / 10** |

### 3.2 Pairwise — each contrast on the largest row set valid for it

Predictors are **not** mutually comparable here; the row sets differ.

| Contrast | rows | CNN | predictor | difference | CI99 |
|---|---|---|---|---|---|
| vs MHCflurry 2.0.0 | 177,313 | 0.6887 | 0.5569 | +0.1318 | [+0.1079, +0.1543] |
| vs MHCflurry 2.3.0 | 176,807 | 0.6866 | 0.5537 | +0.1329 | [+0.1114, +0.1494] |
| vs NetMHCpan 4.1 | 174,481 | 0.6914 | 0.5653 | +0.1261 | [+0.0936, +0.1544] |
| vs MixMHCpred 3.0 | 173,515 | 0.6889 | 0.5544 | +0.1345 | [+0.1075, +0.1588] |

### 3.3 Full partition — D006's secondary, both advantages left in

| System | mean AP | vs CNN |
|---|---|---|
| CNN | 0.7551 | — |
| MHCflurry 2.3.0 | 0.6673 | +0.0877 |
| NetMHCpan 4.1 | 0.6639 | +0.0912 |
| MHCflurry 2.0.0 | 0.6629 | +0.0922 |
| MixMHCpred 3.0 | 0.6606 | +0.0944 |

The CNN value reproduces the endpoint at **0.7551**, the check that this
pipeline scores the same rows the same way. The gaps narrow here because the
predictors gain more from their own overlap than the CNN gains from its.

## 4. The convergence, and what it means

**The four predictors span 0.5434 to 0.5479 — a range of 0.0046.** Three
independent tools, built by three groups, on different training corpora, with
different architectures, one of them trained on 12 million peptides, agree with
each other to within half a percentage point and differ from the CNN together.

**This cuts against reading the gap as architecture.** If a 20,000-parameter
CNN were simply a better model of MHC-I presentation than the state of the art,
the four would be expected to spread out by capability, with the strongest
closing some of the distance. They do not. They cluster, and the cluster sits
0.14 below a model trained on 42 participants of this cohort — same laboratory,
same two instruments, same protocol, same negative construction over this
cohort's own expressed proteins.

That is the signature of a **task-and-distribution advantage, not a modelling
one**, and it is a stronger version of the caveat QC_G11 §4 already carried.

**The predictors are not failing.** A random ranker scores AP = prevalence =
0.440 on the common set. The predictors reach +0.104 to +0.108 over random; the
CNN reaches +0.246. They are doing real work on a question adjacent to ours,
having never seen this cohort.

**The 12-million-peptide question is answered.** NetMHCpan 4.1 is trained on
12,081,588 peptides against MHCflurry's 0.67M, and lands at 0.5472 against
MHCflurry 2.3.0's 0.5479. Training-set size, across this range, buys nothing
here.

## 5. What §18 establishes, and does not

**Establishes.** For the task this dataset defines — separating peptides
observed in a participant's ligandome from unobserved peptides of the same
source proteins — a small CNN trained on this cohort outperforms four
off-the-shelf predictors by about 0.14 average precision, on rows none of them
has seen, in all 10 held-out participants, with four independent contrasts
agreeing to within 0.005.

**Does not establish** that the CNN is a better model of HLA class-I
presentation. §4 is why, and the convergence makes that reading harder to
sustain than it was with two predictors rather than four.

**Not promoted.** D014's condition — every admitted predictor `CLEAN` or
quantified `OVERLAPPING` — is met four times over, and D014 equally bars a
switch after seeing results. §25 was read and closed before any predictor score
existed. §18 stays secondary.

## 6. Limitations

1. **The cohort-specific training advantage is the dominant limitation**, and
   §4 sharpens rather than softens it.
2. **NetMHCpan 4.2 is unscored** — software licence not obtained. Its
   contamination profile would also have made it the weakest comparator of the
   five, for a reason that has nothing to do with its quality.
3. **MixMHCpred drops one allele.** HLA-B\*27:02 is outside its 143
   known-ligand alleles, and the pan-allele path for an unlisted allele needs an
   MHC sequence and a MAFFT alignment rather than a name. UPN27 is scored on
   five of its six alleles. A missing allele can only lose the predictor a true
   positive, so this understates MixMHCpred.
4. **22 ambiguity-code rows** excluded from every system, so all four score
   byte-identical rows.
5. **Partially typed units** are scored on recorded alleles only (D012 imputes
   none), which understates every predictor equally.
6. **Prevalence differs between row sets** (0.440–0.446), so absolute AP
   compares only within a row set.
7. **One cohort, one disease, one laboratory.**

## 7. Reproduction

```
python3 scripts/contamination_all.py <extract-root>
<venv>/bin/python scripts/predict_mhcflurry.py --models <dir> --line 2.3.0
python3 scripts/predict_netmhcpan.py --exe <netMHCpan> --jobs 4
python3 scripts/predict_mixmhcpred.py --repo <checkout> --python-bin <venv/bin>
python3 scripts/compare_predictors_all.py
```
`seed('predictor_bootstrap')` for every interval. Raw predictor output is
retained per unit under `results/predictors/*_raw/`, because re-parsing is free
and re-scoring is 45 minutes — which the `Icore` mistake cost once already.
