# LIMITATIONS

Every limitation of this study, in one place, with its status, what it prevents
the work from claiming, and what would close it.

**Why this file exists separately.** The limitations were first written as §19
of the project report. For a period this repository shipped every headline
number while withholding that report, so the figures were public and the
statement of what they do not support was not. This ledger is shipped
unconditionally so that can never recur (D039).

**That is no longer a hypothetical.** The report is withheld again under D041,
pending submission. This file is therefore the published statement of the
study's limits, not an index to one — it is written to stand alone, and every
entry names the shipped artifact its evidence is in. If you find a limitation
that is stated nowhere in this repository, that is a defect; open an issue.

**Status** is one of:

| | |
|---|---|
| **permanent** | fixed by the data or the design. No analysis of this cohort closes it. |
| **open** | could be closed by work not yet done, in principle. |
| **resolved** | closed, with the closing action named. Kept because a limitation that is removed silently cannot be audited. |

**Measured** limitations have a magnitude in `results/`. The rest are
structural: real, but without a number attached.

---

## 1. Bounding the primary claim

| # | Limitation | Status | Impact | What would close it |
|---|---|---|---|---|
| L1 | **The instrument confound is total.** Two platforms partition the 52 participants 25/27 with **zero overlap**; no participant was run on both. Composition alone separates the platforms at AUROC **0.6404** against **0.5170** for a random-halves control, an excess of **+0.1234** — *measured*, deterministically, in `results/qc/leakage_audit_v2.json` (D053). The superseded figures 0.6451/0.5150 stood in this row until 2026-10-12 and came from a run that could not be reproduced | **permanent** | The endpoint is a *joint* claim about unseen individuals **and** unseen instrument conditions. It cannot be worded as being about biology alone. Stratification bounds the artefact; it does not remove it | A cohort in which platform and participant are crossed rather than nested. R10 bounds the platform cost at 0.04–0.06 AP but cannot subtract it (D005, D025, D053, `results/qc/QC_G5.md`) |
| L2 | **Participant-disjointness is not sequence-disjointness.** **15.99%** of test positives appear verbatim in training on the realised split; 11.76–17.25% across 2,000 random splits — *measured* | **permanent** | The headline figure is inflated. Exposure compounds across 42 training participants rather than staying at the pairwise rate | Nothing, within this cohort. Mitigated, not closed, by reporting the leakage-free subset (84,012 of 100,000 rows) alongside every primary figure (D003). **The 0.0495 gap between the two arms is not an effect of leakage: the subset drops positives only, so prevalence falls 0.500000 to 0.456321. At matched prevalence the leakage-free arm scores 0.7386, so the gap decomposes as prevalence +0.0330 (66.6%) plus a residual of +0.0165 (33.4%). The residual is reported as a residual and not attributed to leakage (D057)** |
| L3 | **The floor is not chance.** A composition-only linear model reaches AP **0.597** against the primary negatives — *measured* | **permanent** | About a fifth of the distance from chance to perfect is available before the network learns any sequence structure. Every figure must be read against 0.597, never 0.5 | Nothing. It is a property of the negative construction and is reported as the baseline (D002) |
| L4 | **Underpowered for a modest effect.** Power **0.42** at true AUROC 0.70, **0.98** at 0.75; minimum reliably detectable lift ≈ **0.14** AP — *measured* | **permanent** | **Failure to reject is not evidence of absent signal.** It is equally consistent with a real effect below the detectable range | More participants. Fixed by the 10 held-out units; no analytic choice improves it (D008) |
| L5 | **Nominal intervals under-cover.** Nominal 95% cluster-bootstrap intervals achieve **0.884–0.890** actual coverage at this participant count — *measured* | **resolved** | Would have overstated precision by that margin | Closed: all intervals are reported at **nominal 99%**, which delivers approximately 95% (`POWER_ANALYSIS.md`) |

**On L4.** The observed lift was 0.158, just above the detectable range, so L4
did not bite on the primary endpoint. It bites hard elsewhere: it is why the
6-unit arm in D031 could not satisfy the criterion D031 itself set, and why the
HLA-C\*07:02 effect is *undetermined* rather than absent. **Having enough power
once is not having enough power.**

---

## 2. The data itself

| # | Limitation | Status | Impact | What would close it |
|---|---|---|---|---|
| L6 | **Negative labels are not evidence of non-presentation.** Negatives are peptides *not observed*, which conflates absence with detection limits. An independently trained predictor ranks **11.78%** of test negatives as strong presenters (percentile ≤ 2) and gives **9.11%** a predicted affinity ≤ 500 nM — *measured, from outside this project* | **open** | Roughly one negative in nine looks presentable to a model that never saw this cohort. The bias is **downward**: every figure here, the endpoint included, is depressed by it | Orthogonal evidence of non-presentation, which mass spectrometry cannot supply. The predictor bound (R13) is the first external constraint, not a count of mislabelled rows |
| L7 | **Low cross-participant overlap may be sampling, not biology.** Only **20.1%** of the union occurs in more than one participant, and overlap barely tracks shared alleles (**4.8%** allele-sharing pairs vs **4.0%** disjoint) — *measured* | **open** | If depth rather than biology explains it, "generalizes to an unseen participant" partly tests generalization across *samples of* a repertoire rather than across repertoires | Deeper sampling. The testable signature is that overlap should rise with per-participant depth; this cohort cannot settle it |
| L8 | **The cohort is uniform and narrow.** All 222 class-I acquisitions are one disease, one tissue, one laboratory, one submission. Age and sex are unavailable for every row | **permanent** | No covariate exists for confound modelling, and **no claim extends beyond this clinical context**. There is no external replication anywhere in this design | A second cohort. This is the single most valuable addition to the work |
| L9 | **The depositor's identification pipeline is inherited and unaudited.** Acquisition files were deliberately not retrieved, so search parameters and error-rate control are taken as given | **permanent** | Positive-set purity is capped at whatever that pipeline achieved. The expected lever — confidence-based re-filtering — was a no-op, removing 0.7% of the union | Retrieving S4 and re-searching. Reading S7, the dataset publication (identified in D037, still not retrieved), is the cheap partial step |
| L10 | **The most load-bearing input has no publisher checksum.** 503 of 504 deposited files carry one; the exception is the metadata file, the sole evidence for sample class, participant identity and genotype | **permanent** | Its integrity rests on our own hash plus agreement with a declared size | The depositor publishing a checksum |
| L11 | **Run-level attribution was not recoverable.** Container-internal references use original laboratory filenames with no intersection with deposited names, under a different participant scheme with no cross-walk | **permanent** | Attribution rests on container filenames, corroborated 1:1 against the 52 metadata participants but not independently verifiable. **A misnamed container at deposition would be undetectable from inside this pipeline** | A cross-walk from the depositor |
| L12 | **Fourteen of 52 participants are incompletely typed.** Each reports *one* allele at one or two loci, making homozygosity and an untyped second allele indistinguishable. **2 of the 23 units used as A\*02:01 non-carriers in D001 and D029 are not certain** — 8.7% — *measured* | **open** | Non-carriage is certain only where the locus is fully typed. The contamination runs in the direction that **weakens** an allele effect rather than manufacturing one | Complete typing. The multi-allele test (§20) already requires locus-certainty throughout; D001 and D029 did not, and are reported with the caveat rather than rerun (D012, D031) |
| L13 | **181 positives carry amino-acid ambiguity codes and the encoder accepted them silently.** X, B (Asx), Z (Glx) in 0.035% of frozen positives and no negatives; the encoder maps an unknown character to the **pad token** — *measured* | **open** | 22 are in the test partition (0.011% of rows), so the endpoint is unaffected at any decimal that matters. The defect is the shape that matters: **input accepted that should have been refused**, the same shape as the encoder bug that once discarded the middle of every peptide longer than eight residues | An encoder that rejects or flags non-standard residues, and a selftest covering them. Found only because MHCflurry refused one of them |

---

## 3. Bounding the secondary claims

| # | Limitation | Status | Impact | What would close it |
|---|---|---|---|---|
| L14 | **The allele result covers one allele.** HLA-A\*02:01 is demonstrated on a symmetric design; HLA-C\*07:02 is not, and HLA-C is untested as a locus | **open** | The effect is small in absolute terms — a few hundredths of AP on strata that are 0.5–5% of each ligandome. **"A\*02:01-exclusive" means exclusive to *carriers*,** which includes peptides restricted by alleles in linkage with it; no deconvolution was done | A second cohort. **The symmetric test cannot be replicated here** — no second allele pair has ≥14 units on both sides (§20, D032) |
| L15 | **The predictor comparison cannot separate architecture from cohort-specific training.** The CNN trained on 42 participants of this cohort — same laboratory, instruments, protocol and negative construction — and the published predictors never saw it | **open** | R10 bounds the instrument part of that head start at 0.04–0.06 AP; **the rest is unquantified.** §18 shows the CNN adds information *on this cohort's task*. It does **not** show the CNN is a better model of HLA presentation | Evaluating on a cohort the CNN never saw. The task is not mismatched: MHCflurry's processing model trains on observed-vs-unobserved at 1:1 with 65% same-protein decoys, nearly the set-C construction |
| L16 | **The four published predictors span only 0.0046 AP.** Three groups, three corpora, three architectures, one trained on 12,081,588 peptides, agreeing with each other and differing from the CNN together — *measured* | **open** | This **weakens** the architectural reading of the CNN's 0.137–0.142 lead. A better presentation model should show the four spreading by capability; they do not. Training-set size buys nothing — NetMHCpan has ≈18× MHCflurry's data and scores 0.5472 against 0.5479 | A second cohort. This is the finding the design did not set out to produce (R14) |
| L17 | **Predictor training data overlaps the test rows.** Contamination measured per predictor and per label; NetMHCpan 4.2's overlap is near-symmetric at 20.74% of positives and 16.20% of negatives — *measured* | **resolved as to measurement** | Quantified rather than assumed, which is why NetMHCpan 4.2 appears in the contamination table and in **no comparison**. The others are admitted as quantified `OVERLAPPING` | Nothing further. The measurement is the mitigation (D006, `results/qc/contamination_all.json`) |
| L18 | *(superseded)* **"Two predictors were never obtained."** | **resolved** | Was true when written, **false as of R14** | Closed by D035 and D036: NetMHCpan 4.1 under the DTU academic licence, MixMHCpred 3.0 from a route the proxy allows. §18 reports all four on a common row set, and the scores are in `results/predictors/`. The superseded paragraph is marked, not deleted, in the withheld report |

---

## 4. The process

| # | Limitation | Status | Impact | What would close it |
|---|---|---|---|---|
| L19 | **The preregistration establishes integrity, not chronology.** The freeze proves artifacts match it and fixes ordering *within* the repository | **permanent** | It does **not** provide independent third-party evidence that it preceded seeing any result: it is created by the repository owner with the owner's clock | A third-party timestamp. A tag was attempted and the remote refused it (D009) |
| L20 | **The model specification was frozen after the data was in hand.** §§11–13 were fixed 2026-10-06, after extraction and dataset construction | **permanent** | No model had been fit and no performance figure existed, so no outcome could have influenced them — **but the length distribution was known**, and it motivated centre-padding. Defensible, declared in §12, but **not blind to the data** | Nothing retrospectively. Freeze the specification before extraction next time |
| L21 | **Several design parameters were chosen by simulation under an assumed model.** The per-participant cap, interval calibration and decision threshold rest on a binormal score model with an assumed between-participant variance | **permanent** | The figures **bound** the design; they do not describe it | Measuring the variance, which requires running the model — circular by construction |
| L22 | **Two preregistered reading rules could not be satisfied by their own designs, and one was narrowed after it failed.** D029 required symmetric confirmation from groups that are not symmetric; D031 required a nominal-99% interval from a 6-unit arm | **open — reader-dependent** | **The most reader-dependent step in this work.** A criterion that bends after it fails is not a criterion. The defences: the failing condition was unattainable by construction, the narrowing was decided by the owner not the author, and the commit history carries the order. **A reader who rejects them should treat §20 as unsupported and the allele result as suggestive, not established** | Nothing retrospectively. A second cohort would test §20 on a criterion fixed in advance (D031, D032) |
| L23 | **One reported result was void and is kept.** D029's allele stratum was defined so one arm had necessarily memorised it — 97.93% of its rows against 0.00%. Its **+0.0660** was the largest number that run produced | **resolved** | Superseded by **+0.0335** on rows neither arm saw. **The second instance of one failure mode** — the first `TEST_LEAKFREE` mask selected a subset with no negatives and returned a perfect 1.0000 — and **both times the broken version produced the most flattering number available** | Closed by D030, which added a standing check. The void result is retained, not deleted |
| L24 | **One run previewed a preregistered result.** Validating the multi-allele code required executing Part B end to end; the direction was visible at 2 epochs and one seed before the full run | **open — trust-dependent** | Nothing remained to choose — every parameter was fixed and committed first — but **a reader must take the commit order on trust** | Validating plumbing on scrambled group labels, which is the practice that avoids it (D031) |
| L25 | **A projection was badly wrong.** Eligible peptides were projected at 1.55M from five participants and measured at **2,658,972** — an error of **−41.8%**, in the direction that made the compute budget optimistic | **resolved as to this estimate** | The compute gate was breached twice. Recorded because a projection never checked against its outcome teaches nothing, and because it is **the clearest available evidence about how much weight the remaining simulation-based figures should carry** | Closed for this estimate by measurement (D022). It stands as a caution over L21 |
| L26 | **The licence question is settled, by permission.** The NetMHCpan 4.1 academic licence §7(v) bars publishing benchmark results to third parties without DTU Health Tech's prior written consent, and §18 is such a benchmark | **resolved — consent granted 2026-10-12** | None. §18 publishes by written consent from DTU Health Tech, obtained before publication rather than assumed. The consent is scoped to what was asked for: the average-precision comparison on the 165,574-row common set and the 199,978-row `Score_EL`/`%Rank_EL` table. It does **not** cover the software, its code or model files, or its verbatim output, and it does not extend to a benchmark on any other row set | Closed. Requested 2026-10-11 under D040, granted 2026-10-12 (D051). The prepared withdrawal (D048) was not executed and is retained as the record that the decision carried no scientific cost. See `THIRD_PARTY_NOTICES.md` §1 |
| L27 | **The environment that produced the model artifacts is inferred, not recorded.** `RUN_LOG.md` carries run records for run-001 to run-006 and run-010 only. Model selection, the final fit, the endpoint read and the predictor comparison have **no run record**, and `final.json`, `endpoint.json` and `selection.json` carry no field naming the Python, numpy or torch version that wrote them. Four environments are recorded in `ENVIRONMENT.md`, two of which differ in numpy version (2.4.6 against 2.1.3) | **open** | The checkpoints' provenance rests on inference from env-002/env-003 rather than on a record. It does not affect the reported numbers — the endpoint reproduces to −4.2e-09 and the leakage distribution exactly under the pinned env-004 — but it means "reproduce this in the original environment" has no precise referent | A run record per artifact, and an environment field written into each result JSON. `requirements.lock` pins the verification environment (D052); the training environment cannot be pinned retroactively |
| L28 | **Sequence recurrence is a perfect label oracle.** Negatives were drawn without replacement across all 52 participants, so no decoy sequence occurs twice, while positives recur up to 15 times. On the held-out partition **P(label = 1 \| sequence seen anywhere in training) = 1.000000** — 15,988 of 15,988, zero negatives seen. A lookup classifier using **no sequence features** scores mean per-participant **AP 0.6426** (nominal-99% [0.6205, 0.6620]) — *measured* | **open** | **Above the preregistered composition floor of 0.597 and above the 0.636 matched floor.** A baseline meant to say what is achievable without learning the task is cleared by something that never reads the peptide. It bounds what the floor means; it does **not** show the network uses the shortcut, which would need an experiment this is not. The leakage-free arm is unaffected — it already excludes every recurring test positive — the primary endpoint is not | A negative pool sampled so that recurrence carries no label information, which means rebuilding the frozen dataset and retraining. `results/qc/QC_G4.md` records the global uniqueness as a passing check; that pass is the mechanism (D056) |

| L29 | **The leakage-free subset removes exact matches only.** `TEST_LEAKFREE.csv` excludes the 15,988 test positives whose sequence occurs verbatim in training, but **402 of the remaining 84,012 rows (0.479%) are one substitution from a training positive** — *measured* by `tests/test_invariants.py` T02 (D060) | **open** | The sensitivity arm is called leakage-free and is not free of near-duplicates. The magnitude is small against the 15.988% exact overlap it does remove, and no claim here rests on the 0.479%; it is recorded because it was never measured before and because "leakage-free" names a stronger property than the file delivers | A split built on sequence distance rather than exact identity, which means rebuilding the frozen split. The test pins the figure so it cannot drift unnoticed |

---

## What would close the most

Three of the four groups above end at the same place. **A second
immunopeptidomics cohort** closes or materially advances L1, L8, L14, L15, L16
and L22 — the instrument confound, the single-context ceiling, the allele result,
the architecture-versus-cohort question, the headline negative finding, and the
only reader-dependent step in the report.

No further analysis of PXD024871 reaches any of them.
