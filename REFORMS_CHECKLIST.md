# REFORMS checklist

Kapoor S, Cantrell E, Peng K, et al. **REFORMS: Consensus-based recommendations
for machine-learning-based science.** *Sci Adv* 2024;10(18):eadk3452.
doi:10.1126/sciadv.adk3452. 32 items across 8 modules.

Every item is answered. Where an item does not apply, it says so **and why** —
an unanswered item and an inapplicable one are different claims, and the
difference is the point of a checklist.

Section references are to `REPORT.md`; decisions are entries in
`DECISION_LOG.md`; limitations are rows in `LIMITATIONS.md`.

**This study is not a method proposal.** It reports what four construction and
design choices cost on one cohort. Several REFORMS items assume a model is
being advanced as useful; those are answered from that standpoint, not
dismissed.

---

## 1. Study goals

| # | Item | Answer |
|---|---|---|
| **1a** | Population or distribution the claim applies to | HLA class-I immunopeptidomes from the 52 participants of PXD024871, measured on two instrument platforms (LTQ 25, Lumos 27). **The claim is about this cohort and is not extrapolated.** L1 and L8 record that a second cohort is what would extend it |
| **1b** | Why that population | It is the largest public class-I immunopeptidome deposit with per-participant HLA genotypes **and** a platform split inside one cohort, which is what makes the instrument confound measurable rather than assumed. D001 |
| **1c** | Why ML was used | The object of study **is** an ML pipeline. The question is what a sequence-only CNN scores once construction artefacts are controlled, so the model is the instrument, not the contribution |

## 2. Computational reproducibility

| # | Item | Answer |
|---|---|---|
| **2a** | Dataset, with link or DOI | PRIDE **PXD024871**; external replication cohort **PXD004023**. `DATA_SOURCES.md` records every source with its SHA-256. Derived tables ship in `data/derived/` |
| **2b** | Code, with link or version | This repository, `scripts/`. Every result is tied to a commit; `freeze_manifest.json` hashes all 396 tracked files. **No Zenodo DOI yet — Q1-017 is open.** This is the one gap in this module |
| **2c** | Computing infrastructure | `ENVIRONMENT.md` records four environments. Training: Tesla T4, torch 2.11.0+cu130. Verification: `requirements.lock`, pinned under D052. **L27 states that the training environment is inferred, not recorded**, for the artifacts written before run records began |
| **2d** | README with instructions | `README.md`; `METHODOLOGY.md` *Execution order* gives the stage sequence |
| **2e** | Reproduction script | `scripts/freeze.py --verify` runs ten checks, including regeneration of every classified artifact (D059) and byte-identical figure regeneration. `tests/run.sh` runs the invariant suite (D060). **Partial:** the 25 checkpoints cannot be retrained here — no GPU — so `train_cnn.py` is exempt by name, with the reason stated |

## 3. Data quality

| # | Item | Answer |
|---|---|---|
| **3a** | Data sources, timing, ground-truth process | PXD024871, a published class-I immunopeptidomics deposit; identifications taken from the depositors' own search output, **not re-searched**. `DATA_SOURCES.md` S1–S7. The ground truth is therefore **the depositors' 5% FDR peptide list**, inherited whole — §18 and L5 |
| **3b** | Sampling frame | The 52 participants with class-I data and a usable genotype, from the deposit's own participant set. `data/derived/FILE_MAP.csv` records the mapping |
| **3c** | Why the dataset suits the task | It carries the three things the questions need together: per-participant identity, per-participant genotype, and two instrument platforms. D001 |
| **3d** | Outcome variable and descriptive statistics | Binary: observed peptide (1) against unobserved expressed-proteome decoy (0). 520,000 each, **1:1 by construction** (D002). Per participant: 10,000 and 10,000 |
| **3e** | Sample size and outcome frequencies | 1,040,000 rows over 52 participants. Held-out: 200,000 rows, prevalence exactly **0.500000** |
| **3f** | Missing data | **None.** Every row carries a sequence, a participant and a label; `tests/test_invariants.py` T06 asserts the counts exactly. 22 held-out rows are excluded from the predictor comparison alone, for HLA allele ambiguity, and are listed in `results/predictors/ambiguity_skipped.csv` |
| **3g** | Representativeness of the sampled dataset | **Not established, and claimed nowhere.** 10,000 peptides per participant is a cap, not a census; the observed universe is 2,658,972 peptides. L1, L8 and L25 carry this. The study's claims are about this cohort |

## 4. Data preprocessing

| # | Item | Answer |
|---|---|---|
| **4a** | Excluded samples and why | Peptides outside 8–12 residues are out of scope (§11). The decoy pool excludes every peptide observed **anywhere in the 52 participants** — this is **D044 defect B**, and `tests/test_invariants.py` T05 pins it at **82,900 sequences withheld using held-out information** |
| **4b** | Impossible or corrupt samples | Decoys are filtered to the 20 standard residues. **Observed peptides are not filtered**, so 181 positive rows over 165 distinct sequences retain B, X or Z. T06 pins both counts. See **6c** — this asymmetry reaches the encoder |
| **4d** | Sampling of the decoy pool | **Size-biased, not uniform, and measured.** `build_dataset.py` reservoir-samples over k-mer *occurrences* and then deduplicates, so a k-mer occurring *m* times in the proteome had roughly *m* times the chance of selection. Frozen decoys carry mean proteome multiplicity **1.47–1.85** across the five lengths against **1.06–1.10** for a uniform draw over distinct eligible k-mers. A replacement pool drawn uniformly, everything else held identical, moves the composition floor by **−0.0011** and the endpoint by **+0.0007** — so the stated sampling property is wrong and no reported number is materially affected (D062, L30) |
| **4c** | Raw-to-input transformations | `FLOWCHART.md` and `METHODOLOGY.md` give the stage chain. Encoding: integers 1–20, 0 = pad, **centre-padded to length 12** so both termini align, which the trainer's selftest asserts is lossless |

## 5. Modeling

| # | Item | Answer |
|---|---|---|
| **5a** | All models trained | A 1-D CNN: embedding(21, E, padding_idx=0) → conv → max-pool → conv → global max → dropout → dense(64) → 1. Selected configuration E=16, C=32, k=3, p=0.0. **25 checkpoints** = 5 CV folds × 5 seeds, ensembled by mean score |
| **5b** | Why this model type | §11 fixed a deliberately ordinary architecture before any data was read. The study asks what construction costs, so the architecture is held fixed and uninteresting on purpose. L15 records that this leaves architecture-versus-cohort unresolved |
| **5c** | Evaluation method, splits and folds | **Participant-disjoint.** 42 participants in 5 CV folds (9/9/8/8/8), 10 held out. A second, independent allele-disjoint partition (29/23) supports the allele analysis. Fixed before any model existed and checksummed in `PREREGISTRATION.md`; T04 asserts the file still matches |
| **5d** | How the reported model was selected | Mean validation average precision across the 5 CV folds, over a 16-point grid, max 100 epochs, early stopping patience 10. `results/model/selection.json` records the criterion and the selected point |
| **5e** | Hyperparameter tuning | Grid of 16 over E, C, k, p. Adam, lr 1e-3, batch 512, BCE-with-logits, max 100 epochs, patience 10. **Tuning used CV folds only; the held-out partition was read once** |
| **5f** | Appropriate baselines | Four: a composition floor (0.597, preregistered), a prevalence floor, three external predictors (NetMHCpan 4.1, MHCflurry 2.0.0/2.3.0, MixMHCpred 3.0), and **a recurrence lookup classifier using no sequence features at all (D056)**. The last one scores **AP 0.6426**, above the composition floor — recorded as L28, not buried |

## 6. Data leakage

| # | Item | Answer |
|---|---|---|
| **6a** | Preprocessing and modeling use training data only | **Violated, knowingly, and measured.** Decoy construction used the full 52-participant observed set, so the negative pool is **not blind to the held-out participants** (D044 defect B). The exposure is bounded adversarially at **−0.0301 AP** (D058) and the withheld count is pinned at 82,900 (T05). Model fitting and hyperparameter selection themselves used CV folds only |
| **6b** | Dependencies or duplicates between train and test | **Measured, not assumed.** Participant-disjoint splitting leaves **15.988% exact sequence overlap** (15,988 of 100,000 held-out positives), because the same peptide is observed in several donors. `TEST_LEAKFREE.csv` defines a sensitivity arm with those rows removed (D003). **The realised overlap exceeds the 95th percentile of 2,000 random splits (15.958%)** — this split leaks more than most, not less (D060). Near-duplicates survive that removal: **402 rows, 0.479%, at Hamming distance 1** (L29). The leak-free arm's AP is **0.7056** against **0.7551**, and D057 shows that gap is **66.6% prevalence, 33.4% residual** — *not* an effect of leakage |
| **6c** | Each feature legitimate, no outcome leakage | **Two exact label oracles exist and both are disclosed.** (i) No decoy sequence occurs twice in the dataset while positives recur, so *P(label = 1 \| sequence seen in training) = 1.000000* on the held-out partition, with no counter-example in 520,000 decoys (D056, L28). (ii) The ambiguity-code asymmetry, already reported as the third of our own defects; completing this item identified its **mechanism**. `encode()` maps B, X and Z to **0, the padding token**, so all **181** B/X/Z positive rows carry a zero at a position where **no decoy of that length ever has one** — 0 of 520,000 decoys show a non-canonical zero pattern. **22 of those rows are in the held-out partition (0.011% of it).** The magnitude is negligible for the endpoint; the mechanism is an exact label leak through the encoder, and it is recorded rather than rounded away |

## 7. Metrics and uncertainty quantification

| # | Item | Answer |
|---|---|---|
| **7a** | Metrics listed, selection metric justified | Mean per-participant **average precision** (D008): the participant is the unit of analysis, so pooling rows across participants would treat one donor's 20,000 rows as 20,000 independent observations. AP's floor is the prevalence, which is why D057 had to separate the prevalence shift from the leak |
| **7b** | Uncertainty estimates and how computed | **Cluster bootstrap over participants**, B = 10,000, **nominal 99%**. Nominal 99% is used because R6 measured nominal-95% delivering only **0.884–0.890** actual coverage at this unit count — so **no 99% confidence is claimed**, and the interval is reported as nominal. Primary: 0.7551 [0.7368, 0.7721] |
| **7c** | Statistical tests justified, assumptions checked | The primary decision is a **preregistered threshold rule**, not a test: reject if the lower bound exceeds 0.647, fixed by `calibrate_decision_rule.py` before the endpoint was read. The cluster bootstrap's assumption — exchangeable participants — is stated, and R6 is the check on it |

## 8. Generalizability and limitations

| # | Item | Answer |
|---|---|---|
| **8a** | Evidence of external validity | **One external cohort, PXD004023**, replicating the platform-composition effect at **+0.0469 with an interval** (D055). That is the whole of the external evidence, and it covers one of four findings |
| **8b** | Where the findings are not expected to hold | `LIMITATIONS.md` carries **30 rows**. The binding ones: a single cohort (L1, L8), inherited identifications at 5% FDR (L5), no causal attribution to instrument physics or to leakage (L2, D057), the decoy construction, whose sampling bias is now measured but whose expression-restricted design no analysis here revisits, and the confounds both platforms and both allele groups **share** — source-protein abundance, detectability bias, the decoy construction — which no analysis in this study can reach |

---

## Where this study fails REFORMS

Three items are not satisfied, and listing them is more useful than a clean
table.

1. **2b — no persistent identifier.** The code is committed and hashed but has
   no DOI. Q1-017 is open.
2. **3g — representativeness is not established.** 10,000 peptides per
   participant is a cap. The study does not claim the sample represents the
   immunopeptidome, and a reader should not read it that way.
3. **6a and 6c — leakage is present, not absent.** REFORMS asks authors to
   *justify that the study avoids* these sources. This study cannot: it
   measures them instead, which is its subject. **A checklist answered
   "measured, not avoided" is a different document from one answered
   "avoided", and the distinction should survive into review.**
