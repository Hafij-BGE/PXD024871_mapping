# Analysis plan — PXD004023 workflow-confound replication

**Written before any classifier was run on this dataset.** Fixed in advance so
the reading of the result is not chosen after seeing it. This plan does **not**
modify, extend or reinterpret the PXD024871 preregistration, which is frozen and
unchanged.

## What is being tested

Whether a composition-only classifier can separate peptides by **acquisition
workflow** in an independent cohort from an independent laboratory.

**This is not an instrument-only replication.** In PXD004023 the instrument is
completely confounded with two other factors:

| Factor | 2013 arm | 2014 arm |
|---|---|---|
| Instrument | Orbitrap Elite | Q Exactive Plus |
| Acquisition year | Dec 2013 | May–Oct 2014 |
| Fractionation | SCX, 5 fractions (50/75/100/300/600 mM) | none |

All 160 runs: 95 Elite, all fractionated, all 2013; 65 Q Exactive Plus, none
fractionated, all 2014. **No run breaks the pattern.** A positive result
therefore supports "the acquisition workflow leaves a learnable signature in
peptide sequence" and **cannot** attribute that signature to the instrument.

**SCX fractionation separates peptides by charge**, which is a direct function
of amino-acid composition — the exact feature space the classifier uses. This is
an adversarial confound for this specific test and must be stated wherever the
result appears.

## Cohort and units

**Primary cohort:** the 6 donors with data on both workflows — C, CELG, J, MA,
PF1, RT. All are B-lymphoblastoid cell lines derived from volunteer PBMCs
(Pearson et al., *J Clin Invest* 2016; PMID 27841757), so material type is
constant across the comparison.

**Evaluation unit: the donor.** Runs and SCX fractions are technical
subdivisions of one biological sample and are **not** independent replicates.
Treating them as such would be pseudoreplication. Peptides are pooled to one set
per (donor, workflow); the 6 donors give 6 paired observations.

**Secondary cohort:** the 12 donors with 2014 data only, reported separately and
never pooled with the primary comparison.

## Inclusion and exclusion

- Include: peptide sequences from the PEAKS `.mzid` identification results, as
  deposited. No re-searching, no re-scoring.
- Exclude: sequences containing non-standard residues, to match the frozen
  procedure's 20-letter alphabet.
- No length window is imposed beyond what the deposit contains. **If the length
  distributions differ between arms, that is reported, not corrected** — it is
  part of the workflow signature, exactly as the 12-mer difference was in
  PXD024871.
- No decoys, no negative construction, no proteome: both classes are observed
  peptides.

## Procedure, held to the frozen method

From `scripts/leakage_audit.py` (PXD024871), unchanged in substance:

- 20-dimensional amino-acid composition, fractions, **no positional
  information**.
- Fisher linear discriminant, closed form.
- Class balance by subsampling to the smaller arm.
- AUROC with midrank tie correction.

**The classifier is refitted on this cohort. That is the method, not a
deviation** — the frozen procedure fits on training units and scores held-out
units; it was never a portable fitted model.

**One deliberate strengthening.** The PXD024871 procedure pools peptides by
platform and then splits 50/50 at the peptide level. Here evaluation is
**leave-one-donor-out**: a donor's peptides appear in training or in test, never
both. This removes donor leakage the original design permitted. It makes the
test harder, not easier, and the difference is reported.

## Controls

1. **Random-halves control**, as in the frozen procedure: split the 6 donors
   into two random halves, pool each half across both workflows, and classify
   half A against half B. This measures separability attributable to donor
   identity rather than workflow.
2. **Within-donor consistency**: report the per-donor held-out AUROC, not only
   the mean. A workflow signature should appear in every donor.

## Interpretation, fixed in advance

- **AUROC near 0.5** on the workflow test → no detectable workflow signature in
  this cohort. Reported as a negative result. It would **not** overturn the
  PXD024871 finding, because the cohorts, instruments and protocols differ; it
  would bound the generality of the claim.
- **AUROC clearly above the random-halves control** → a workflow-associated
  composition signature replicates in an independent cohort and laboratory,
  with instrument, year and fractionation inseparable.
- **AUROC above 0.5 but not above the control** → donor identity, not workflow,
  is what is separable. Reported as such.

**No outcome licenses a causal instrument claim.** The original PXD024871
finding — platform separability at AUROC 0.6451 against a 0.5150 control, where
platform was confounded with participant but not with fractionation — remains a
separate and more specific result, and is not amended by anything here.

## Reporting

Every result table carries instrument, year and fractionation labels together.
Sample counts are reported at donor, run and fraction level separately.

## Restrictions honoured

No PXD024871 artifact, result, manuscript, supplement, `RUN_LOG.md` or decision
entry is modified. Nothing is committed, pushed, published or minted. Download
ceiling 3 GB: 161 MB of raw headers plus 1.13 GB of identification results,
≈1.29 GB used.
