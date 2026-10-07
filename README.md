# PXD024871 — a preregistered sequence-only CNN benchmark on HLA class-I immunopeptidomics

A single-cohort study asking whether a 1D CNN can tell experimentally observed
HLA class-I peptides from matched decoys using **sequence alone**, and how it
compares with five published presentation predictors on identical rows.

It is also, deliberately, a record of **how** the answer was reached: every
decision, every gate, and every analysis that turned out to be wrong is in this
repository, including the two occasions on which a bug produced the most
flattering number available and had to be withdrawn.

> **Status:** complete and frozen. Checksum-verified at `freeze_manifest.json`.
> **Not peer reviewed.** One cohort, 52 participants, 10 held-out test units.
> The limits in `REPORT.md` §19 are not boilerplate — read them before reusing
> any number here.

---

## What was found

| | |
|---|---|
| Primary endpoint, held-out units | **AP 0.7551** (99% CI 0.7368–0.7721) |
| Same model, leakage-free rows only | AP 0.7056 — the 0.0495 gap is sequence overlap, measured rather than assumed |
| Composition-only LDA floor | 0.597 pooled — so the CNN is reading more than amino-acid frequency, but the floor is high |
| Cross-platform transfer (LTQ↔Lumos) | 0.6959 / 0.7108 — does not collapse; platform costs 0.04–0.06 AP |
| Allele-exclusive signal (A\*02:01) | +0.0476 (99% CI +0.0314 to +0.0626), 9/9 units |

**The headline is a negative result about the predictors.** On 165,574 rows
common to all systems (prevalence 0.440):

| System | Mean AP |
|---|---|
| CNN (this work) | **0.6852** |
| MHCflurry 2.3.0 | 0.5479 |
| NetMHCpan 4.1 | 0.5472 |
| MHCflurry 2.0.0 | 0.5443 |
| MixMHCpred 3.0 | 0.5434 |

Four independently built predictors — three groups, three corpora, three
architectures, one trained on 12,081,588 peptides — **span 0.0046**. They agree
with each other and differ from the CNN together.

Read that carefully, because it cuts against the flattering interpretation.
If the CNN's +0.137 to +0.142 lead reflected a better model of presentation,
the four predictors should spread out by capability. They do not. Training-set
size buys nothing: NetMHCpan has roughly 18× MHCflurry's data and scores 0.5472
against 0.5479. The more likely reading is that the CNN is partly fitting
properties of **this cohort's negative construction**, which the predictors
never saw, rather than presentation as such. `REPORT.md` §18–§19 argues this
at length and does not resolve it. **A second cohort would.**

Contamination was measured, not assumed: each predictor's training data was
checked against our test rows and the overlap is reported per predictor and per
label (`results/qc/contamination_all.json`). NetMHCpan 4.2's overlap is
near-symmetric (20.7% of positives, 16.2% of negatives), which is why it
appears in the contamination table and in no comparison.

---

## Repository layout

```
PREREGISTRATION.md      hypotheses, estimand and artifact hashes, committed
                        before any model was trained
DECISION_LOG.md         D001–D038, every decision and every reversal
DATA_SOURCES.md         twelve provenance fields per source
FLOWCHART.md            pipeline shape
FREEZE_RECORD.md        the freeze and what it verifies
CITATION.cff            how to cite this work

scripts/                29 scripts; the pipeline, the QC, the figures
data/derived/           the frozen analysis tables
results/figures/        F1–F13, standalone SVG, dark-mode aware
results/qc/             gate records
results/model/          endpoint artifacts and model weights
notebooks/              Colab runners used for the bulk extraction
freeze_manifest.json    SHA-256 of every tracked file
```

### Documents not published here

Nine documents are part of this project and are **not in this repository**:

`REPORT.md` (the findings) · `METHODOLOGY.md` · `SECTIONS.md` ·
`POWER_ANALYSIS.md` · `THIRD_PARTY_NOTICES.md` · `PROJECT_PROMPT.md` ·
`RUN_LOG.md` · `ENVIRONMENT.md` · `HANDOVER.md`

They are withheld at the project owner's decision (D038) — internal working
documents, and a result held pending submission. References to them elsewhere in
this repository are left **as written** rather than edited away, so they point at
this note rather than at nothing.

Two consequences worth stating rather than leaving to be discovered:

- **`scripts/freeze.py --verify` will not run on a clone.** Three of its nine
  checks read `REPORT.md` and it is not here. It still passes for anyone holding
  the full tree.
- **The withheld documents remain in this repository's git history.** Untracking
  removes a file from the published tree, not from the commits that carried it.
  Anyone who clones can recover them. This is recorded, not relied upon.

To ask for any of them, open an issue.

## Verifying and reproducing

The freeze is verification-gated: the manifest refuses to be written over a
tree that does not pass its checks.

```bash
python3 scripts/freeze.py --verify
```

Nine checks: working tree clean · the preregistration hashes still hold · every
path `REPORT.md` names resolves · 44 headline numbers appear verbatim in
`REPORT.md` · the figures regenerate byte-identically · every gate PASSED ·
every decision resolved · the manifest agrees with the tree · the trainer's
selftest passes.

```bash
python3 scripts/train_cnn.py --mode selftest   # encoder, AP, gradients, overfit
python3 scripts/make_figures.py                # regenerates F7–F13 from results/*.json
```

Full re-execution needs the PRIDE payloads (`data/raw/**`, gitignored — tens of
gigabytes; URLs and digests are committed) and, for §18, the three predictors
installed under their own licences. Seeds derive deterministically by SHA-256
from a recorded base (`scripts/seeds.py`), so runs reproduce.

## What is deliberately not here

- **Acquisition payloads and third-party training corpora** — `data/raw/**`.
  Too large, and S5/S6 carry their own terms. Provenance and SHA-256 committed.
- **Verbatim NetMHCpan and MixMHCpred stdout** — `results/predictors/*_raw/`.
  The per-peptide scores *are* committed.
- **The T-A4 experiment proposal** — an internal, unpreregistered document.
  Withheld under D037; its title, size and SHA-256 are in the stub beside it,
  so references to it still resolve to something verifiable.

Nothing was deleted to make a result look better. Rejected and failed analyses
stay on the record with the reason — see D029/D030 (an allele stratum 97.93%
memorised by one arm, whose +0.0660 was void and was corrected to +0.0335) and
D031/D032 (a release criterion that was unattainable as written, narrowed on
the record rather than quietly dropped).

## Licensing

| What | Licence |
|---|---|
| `scripts/`, `notebooks/` | MIT — `LICENSE` |
| Documents, figures, `results/`, `data/derived/` | CC BY 4.0 — `LICENSE-docs` |
| Predictor output and third-party data | **Not covered by either.** See the third-party note below |

Two carve-outs matter and are not negotiable by this repository:

- **MixMHCpred-derived files** are restricted by the Ludwig Institute licence to
  **academic non-commercial** use, which CC BY 4.0 cannot widen.
- **NetMHCpan 4.1's licence** bars publishing benchmark results to third parties
  without DTU Health Tech's prior written consent (§7(v)). Read your own
  licence grant before republishing the comparison; it is easy to miss.

## Citation

See `CITATION.cff`, or use GitHub's "Cite this repository". Cite the predictors
and the underlying deposit as well as this repository; `CITATION.cff` lists the
deposit, its publication, and the three predictor papers.

The data are from PRIDE Archive
[PXD024871](https://www.ebi.ac.uk/pride/archive/projects/PXD024871). This
repository is an independent reanalysis and is not affiliated with the original
depositors.

## Contributing and corrections

Issues and corrections are welcome, particularly on the licence readings in
the licence readings and on the §18 interpretation. If you have a second
immunopeptidomics cohort, the single most useful thing anyone can do with this
repository is try to break the 0.6852 on data it has never seen.
