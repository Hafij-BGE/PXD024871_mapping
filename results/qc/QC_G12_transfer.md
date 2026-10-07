# QC G12 (part) — Cross-platform transfer · D025, D028

**Run:** 2026-10-07 · `scripts/train_cnn.py --mode transfer` · CPU, torch 2.14.1
**Artifacts:** `results/model/transfer.json`, `results/model/transfer_posthoc.json`,
`results/model/transfer.log`, 20 checkpoints `transfer_*_s*.pt`
**Configuration:** `{E:16, C:32, k:3, p:0.0}` — taken from `selection.json`, not re-tuned
**Replicates:** 5 seeds per arm from `seed('transfer_init', ·)`; per-unit AP is the
mean across the 5 models, as D027 fixed
**Status: PASSED. The §25 claim survives cross-platform transfer. A real but
bounded platform effect is measured, not inferred.** G12 as a whole is not
passed — §18 remains blocked by D006.

---

## 1. What was asked

D025, preregistered before any model was trained: *"Train on the 25 LTQ units
and test on the 27 Lumos units, then the reverse. ... If performance holds
within platform and collapses across, the §25 claim is substantially about
instrument rather than biology."*

D028, logged before this run and after none of its numbers were visible, kept
that verbatim and added a matched within-platform control, because the
preregistered arms alone confound platform with training-set size, and because
the pooled 0.597 floor is not the composition separability of a cross-platform
test set.

## 2. Results

Mean per-unit average precision; participant is the cluster; nominal-99%
cluster bootstrap, B = 10,000 (D008). Every floor is a composition-only LDA
fitted on **that arm's own training rows** and scored on **that arm's own test
rows**, by the D002 method.

| Arm | train | test | mean AP | CI99 | own floor | lift over own floor | lift CI99 | per-unit range |
|---|---|---|---|---|---|---|---|---|
| **P_LTQ_to_Lumos** (D025) | 20 LTQ | 27 Lumos | **0.6959** | [0.6805, 0.7113] | 0.5917 | **+0.1042** | [+0.0918, +0.1163] | 0.6316–0.7644 |
| **P_Lumos_to_LTQ** (D025) | 22 Lumos | 25 LTQ | **0.7108** | [0.6993, 0.7221] | 0.6093 | **+0.1015** | [+0.0931, +0.1098] | 0.6677–0.7582 |
| M_LTQ — within (D028) | 10 LTQ | 12 LTQ | 0.7481 | [0.7244, 0.7743] | 0.6648 | +0.0833 | [+0.0696, +0.0996] | 0.6878–0.8140 |
| M_LTQ — across (D028) | 10 LTQ | 13 Lumos | 0.6879 | [0.6608, 0.7142] | 0.5919 | +0.0961 | [+0.0816, +0.1122] | 0.6261–0.7548 |
| M_Lumos — within (D028) | 10 Lumos | 13 Lumos | 0.7379 | [0.7244, 0.7499] | 0.6158 | +0.1221 | [+0.1075, +0.1372] | 0.7069–0.7615 |
| M_Lumos — across (D028) | 10 Lumos | 12 LTQ | 0.6965 | [0.6791, 0.7140] | 0.6102 | +0.0863 | [+0.0734, +0.0986] | 0.6575–0.7307 |

Seed spread within an arm: 0.0016–0.0050 validation AP. Replicate noise is not
driving anything below.

### 2.1 The preregistered arms do not collapse

D008's rule is: reject if the lower bound of the nominal-99% interval exceeds
floor + 0.05.

| Arm | lower bound | pooled threshold (0.597 + 0.05) | arm-specific threshold (own floor + 0.05) | verdict |
|---|---|---|---|---|
| P_LTQ_to_Lumos | 0.6805 | 0.647 | 0.6417 | clears both |
| P_Lumos_to_LTQ | 0.6993 | 0.647 | 0.6593 | clears both |

A model that has never seen a single run from the target instrument predicts
held-out participants on that instrument well above what composition alone
achieves on the same rows. The preregistered collapse condition is **not met,
in either direction.**

### 2.2 But a platform effect is there, and both contrasts agree

| Contrast | holds constant | moves | difference | CI99 | units degraded |
|---|---|---|---|---|---|
| **A** · M_LTQ | the model | test platform | +0.0601 | [+0.0243, +0.0979] | unpaired |
| **A** · M_Lumos | the model | test platform | +0.0414 | [+0.0200, +0.0631] | unpaired |
| **B** · LTQ held-out half | the test units | training platform | +0.0516 | [+0.0261, +0.0745] | 10 / 12 |
| **B** · Lumos held-out half | the test units | training platform | +0.0500 | [+0.0295, +0.0741] | 13 / 13 |

Four estimates, two designs, no interval containing zero. Training on the other
platform costs **0.04 to 0.06 AP**. Contrast A holds the model identical and
moves the test platform; contrast B holds the test units identical and moves the
training platform. They agree to within 0.01, so the effect is not an artefact
of either the model or the particular test set.

That is a cost, not a collapse: the across-platform arms sit 0.05 below their
within-platform counterparts and 0.09–0.10 **above** their own composition
floors.

### 2.3 Post-hoc — how much of the penalty is composition?

**Not preregistered.** Derived in `results/model/transfer_posthoc.json` from
per-unit values already stored; no model was retrained, nothing was refitted,
and the question was asked because §2.2's floors moved between arms. Paired per
unit on each test half: the CNN's cross-platform penalty against the penalty a
20-parameter composition-only linear model pays on the *same units*.

| Test half | CNN penalty | composition-only penalty | excess (CNN − composition) | CI99 | units with excess > 0 |
|---|---|---|---|---|---|
| LTQ held-out half (12) | +0.0516 [+0.0267, +0.0744] | +0.0545 [+0.0217, +0.0854] | **−0.0030** | [−0.0137, +0.0073] | 5 / 12 |
| Lumos held-out half (13) | +0.0500 [+0.0291, +0.0745] | +0.0239 [+0.0003, +0.0509] | **+0.0261** | [+0.0176, +0.0349] | 13 / 13 |

**The two halves give different answers, and the asymmetry is the finding.**
Predicting LTQ participants from a Lumos-trained model, the CNN loses no more
than amino-acid frequencies alone lose — the interval spans zero and the sign is
split 5/12, so on that half the platform effect *is* a composition shift, which
the CNN inherits rather than compounds. Predicting Lumos participants from an
LTQ-trained model, the CNN loses 0.026 more than composition does, with every
one of the 13 units in the same direction. Something about Lumos peptides beyond
their composition is learned from Lumos data and not from LTQ data.

D025 already named a mechanism in that direction: 12-mers are 11.69% of LTQ
positives against 9.85% of Lumos. Length-dependent detectability is positional,
not compositional, and a convolutional model over centre-padded sequences can
use it. This is a consistent reading, not a demonstrated one — the analysis
measures the excess, it does not attribute it.

## 3. What this does and does not establish

**Establishes.** The §25 lift is not solely an instrument signature. A model
trained on one mass spectrometer ranks held-out participants' peptides on the
other mass spectrometer 0.09–0.10 AP above that pairing's own composition floor,
with intervals excluding the D008 threshold. The pre-committed interpretation
*"Rejects, but collapses in cross-platform transfer → the signal is
substantially instrument, not presentation"* **does not apply to this result.**

**Does not establish.** That the retained signal is presentation biology. Ruling
out instrument-specific signature leaves every *shared* non-presentation source
untouched: source-protein abundance, proteolytic and detectability biases common
to both instruments, and the set-C negative construction itself (D002: 0.6085
composition AUROC against positives, which is why floors here run 0.59–0.66
rather than near 0.5). A cross-platform result cannot distinguish presentation
from any confound both platforms share. **The allele-disjoint analysis (D001) is
the next one that bears on biology, and §20 should not be written as biology
before it runs.**

**Does not remove the confound.** No unit spans both platforms (D005), so
platform and participant stay perfectly nested. This measures the confound's
size; nothing here recovers a platform-free estimate.

## 4. Limitations of this analysis specifically

1. **The preregistered arms train on 20 of 25 and 22 of 27 units**, not all of
   them: 5 units per arm are the unit-disjoint early-stopping set. Stopping on
   target-platform rows would have been leakage; stopping on peptide-level
   splits within the training units would have broken the unit-disjointness the
   rest of the pipeline maintains. Recorded in D028, and it biases both arms the
   same way.
2. **The matched arms train on 10 units against the primary fit's 42.** Their
   absolute numbers are therefore **not** comparable to the primary endpoint's
   0.7551, and no such comparison is made. Only the within-versus-across
   contrast inside them is interpretable, which is what they were built for.
3. **All four arms train on units inside the primary test partition.** These
   models are used for this analysis only and never for §25, which was read once
   and is closed. Stated rather than worked around.
4. **Each half is 12 or 13 units.** The contrast-B intervals are the tighter
   ones because they are paired, but 12 units is 12 units: the effect is
   established in sign and order of magnitude, not to the third decimal.
5. **§2.3 is post-hoc.** It is reported as a diagnostic that generated a
   hypothesis about length, not as a test of one.

## 5. Reproduction

```
python3 scripts/train_cnn.py --mode transfer
```

Refuses to run without `selection.json` (it must not tune its own
configuration) and without `endpoint.json` (it trains on primary-test units, so
it must follow the single preregistered read). Halves from
`seed('transfer_halves')` = 952257691, early-stopping holdouts from
`seed('transfer_valsplit')`, weights from `seed('transfer_init', i)`, intervals
from `seed('transfer_bootstrap')`, §2.3 from `seed('transfer_posthoc')`.
Shortened runs write to `transfer.PARTIAL.json` under a separate checkpoint
namespace, so a plumbing test cannot be reused as a cached model by a full run —
one 2-epoch single-seed plumbing test was run on M_LTQ before this, and its
artifacts were discarded as a test rather than kept as a rejected analysis.
