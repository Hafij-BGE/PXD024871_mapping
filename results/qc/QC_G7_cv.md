# QC_G7 — model selection

run-013, on Colab CUDA (`env-003`). 16 configurations × 5 folds, the complete
preregistered grid. **The held-out partition was not read.**

| Result | Check | Detail |
|---|---|---|
| PASS | Grid complete | 16 / 16 configurations at the full epoch budget |
| PASS | Selection record written | only a complete grid can write it; it unlocks `--mode test` |
| PASS | Test partition untouched | `--mode cv` reads only the 42 CV units |
| PASS | Selftest passed on this hardware | encoding lossless, gradients verified, planted signal recovered |

**Selected:** `E=16, C=32, k=3, p=0.0` — mean validation AP **0.7525**.

## The grid is flat, and that is the finding

| | |
|---|---|
| Best configuration | 0.7525 |
| Worst configuration | 0.7396 |
| **Between-configuration spread** | **0.0129** |
| **Within-configuration fold spread (mean)** | **0.0117** |
| SD of the 16 configuration means | 0.0036 |
| Mean standard error of a configuration mean | 0.0020 |

**The best configuration beats the worst by less than a single configuration's
folds vary among themselves.** Selecting among these 16 is not distinguishable
from selecting at random.

Per hyperparameter, averaged over the rest:

| Hyperparameter | Effect on mean validation AP |
|---|---|
| embedding dim (16 vs 32) | 0.0006 |
| filters (32 vs 64) | 0.0012 |
| kernel (3 vs 5) | 0.0008 |
| dropout (0.0 vs 0.3) | 0.0055 |

Only dropout registers at all, and it **hurts**. The selected configuration is
the smallest in the grid.

## What this costs and what it buys

The grid spent **80 of the 105 preregistered runs** choosing between options
that differ by less than fold noise. On the face of it that is waste, and §13's
own limitation anticipated the opposite problem — that a 16-point grid might be
too small.

It is not waste, for a reason worth stating. A flat grid means the eventual
result **cannot be attributed to architecture choice**, because no architecture
in the searched family does meaningfully better than any other. Had the grid
been steep, a reader would be entitled to ask how much of the result came from
selecting a lucky configuration. It did not, and now that question is answered
with a measurement rather than an assurance.

It also says something about the task: capacity is not the binding constraint
at this dataset size. Whatever limits performance here, it is not the size of
the network.

## Validation level, stated with its caveat

Best configuration reaches **0.7525** on validation against a composition-only
floor of **0.597** — a lift of +0.1555, well clear of the 0.647 decision
threshold.

**This is not the result.** It is validation performance on CV folds drawn from
the same 42 participants used for selection. The endpoint is the held-out
partition, which carries 15.99% sequence leakage and a platform confound that
the CV folds share rather than control. The test partition remains unread.

## Gap found and closed before reading the endpoint

§13 required all 25 final models be reported but never said **how 25 models
produce the one number the decision rule applies to.** Found while implementing
the evaluation, with the test partition still unread, and closed as D027:
per-unit AP is computed under each model and averaged across the 25, the
estimand is the mean of those per-unit values, and score-ensembling is reported
only as a secondary figure — an ensemble of 25 networks answers a more
flattering question than §25 asks.
