# Third-party notices

This repository's own licences (`LICENSE`, `LICENSE-docs`) cover only what the
project owner holds rights to. They **cannot** and do not grant rights over
third-party software, third-party data, or output restricted by a third party's
terms. This file records, per third party, what was used, under what terms, and
which files in this repository are affected.

Bibliographic details below were verified against PubMed on 2026-10-07 rather
than cited from memory. Licence terms are quoted from the licence text actually
accepted at download, where that text is held; where it is not held, this file
says so instead of paraphrasing.

---

## 1. Read this before making this repository public

**One clause needs resolving first.** The NetMHCpan 4.1 academic licence
(§7, "Software Protection") states that the licensee may not:

> (v) publish any results of benchmark tests run on the Product to a third
> party without HEALTH's prior written consent.

Section 18 of `REPORT.md` is a benchmark of NetMHCpan 4.1 against four other
systems, and reports its average precision. On a plain reading, publishing it
to the world is publishing a benchmark result to third parties, and the clause
asks for DTU Health Tech's prior written consent first.

Three things should be said honestly alongside that:

1. **This is a reading of the text, not legal advice.** I am not a lawyer and
   this is not a legal opinion.
2. **Publishing NetMHCpan benchmarks is near-universal practice** in this
   field, including in papers by groups unaffiliated with DTU, and including
   the MHCflurry 2.0 paper cited below, which benchmarks against NetMHCpan 4.0
   in its abstract. That practice suggests the clause is not enforced against
   ordinary scientific comparison. It does not establish that consent was
   given, and it is not verified here.
3. **The clause is generic boilerplate, not NetMHCpan-specific drafting.** The
   same licence's §10 requires that "any reference to the software for
   *crystallographic computations*" cite the manual — a provision carried over
   from an unrelated package. That is evidence about how the document was
   assembled, not a licence to ignore §7(v).

**Resolution is cheap:** the contact named on the service page for software
licensing is `health-software@dtu.dk`. One email asking for written consent to
publish the comparison settles it. Until it is settled, the options are to ask
first, to publish without the NetMHCpan arm (the other four systems stand on
their own, and §18's headline — that the predictors span 0.0046 — survives with
three of them), or to proceed on the practice argument above with this notice
on the record. That choice belongs to the project owner.

---

## 2. Prediction software

None of the three predictors' code is in this repository. Each was installed
outside the repository tree and invoked from there, so no part of this
repository redistributes any of them.

### NetMHCpan 4.1 — DTU Health Tech

| | |
|---|---|
| Licence | DTU Health Tech academic licence, accepted at download 2026-10-07 |
| Terms held | Yes — `netMHCpan-4.1_license.txt`, shipped with the package, retained outside this repository |
| Grant | Non-exclusive, non-transferable, free of charge, to a non-profit educational/academic/research institution, "for personal and internal use in research only at one Site" |
| Prohibited | Redistribution or transfer of the software; modification without written consent; any use resulting in commercialization; **publishing benchmark results to third parties without prior written consent (§7(v), see above)** |
| In this repository | `results/predictors/netmhcpan_4_1_test_scores.csv`; the NetMHCpan rows of `results/qc/predictor_comparison_all.json`, `results/qc/contamination_all.json` and §18 of `REPORT.md`; `data/derived/TEST_PREDICTOR_OVERLAP_NetMHCpan_4_1.csv` and `..._4_2.csv` |
| Not in this repository | The software; its verbatim stdout (`results/predictors/netmhcpan_raw/`, gitignored); the 4.2 training set (`data/raw/S6/`, gitignored) |

Citation, as the service page requires. According to PubMed: Reynisson B,
Alvarez B, Paul S, Peters B, Nielsen M. *NetMHCpan-4.1 and NetMHCIIpan-4.0:
improved predictions of MHC antigen presentation by concurrent motif
deconvolution and integration of MS MHC eluted ligand data.* Nucleic Acids
Research 2020;48(W1):W449–W454.
[DOI 10.1093/nar/gkaa379](https://doi.org/10.1093/nar/gkaa379) · PMID 32406916.

### MixMHCpred 3.0 — Ludwig Institute for Cancer Research

| | |
|---|---|
| Licence | LICR "Software License Agreement for Academic Non-Commercial Research Purposes Only" |
| Terms held | Yes — `MixMHCpred_license.pdf`, shipped with the package, retained outside this repository |
| Grant | Non-exclusive, non-transferable, academic non-commercial research only: download, execute, display, and create bug fixes or modifications |
| Prohibited | Sublicensing or distributing the program; placing it on a network accessible to anyone who has not accepted the agreement; any commercial purpose |
| **Output** | §2.1 expressly permits providing results: the licensee "may apply the PROGRAM in a pipeline to data owned by users other than the LICENSEE and provide these users the results of the PROGRAM **provided LICENSEE does so for academic non-commercial purposes only**" |
| In this repository | `results/predictors/mixmhcpred_3_0_test_scores.csv`; the MixMHCpred rows of the comparison and contamination JSONs and §18 of `REPORT.md`; `data/derived/TEST_PREDICTOR_OVERLAP_MixMHCpred_3_0.csv` |
| Not in this repository | The software; its verbatim stdout (`results/predictors/mixmhcpred_raw/`, gitignored); the training table (`data/raw/S6/`, gitignored) |

> **Carve-out from this repository's CC BY 4.0 grant.** CC BY 4.0 permits
> commercial reuse. The project owner cannot grant that over MixMHCpred output,
> because §2.1 restricts it to academic non-commercial purposes. The
> MixMHCpred-derived files named above are therefore **excluded from the CC BY
> 4.0 grant** and may be used for academic non-commercial purposes only.
> For-profit users must obtain a licence from LICR; the README names Nadette
> Bulgin (`nbulgin@lcr.org`) at the Ludwig Institute for Cancer Research Ltd.
> Copyright (2024) David Gfeller.

Citation, as the README requires. According to PubMed: Tadros DM, Racle J,
Gfeller D. *Predicting MHC-I ligands across alleles and species: how far can we
go?* Genome Medicine 2025;17(1):25.
[DOI 10.1186/s13073-025-01450-8](https://doi.org/10.1186/s13073-025-01450-8) ·
PMID 40114147.

MixMHCpred's installer additionally fetches MAFFT, which carries its own
licence (<https://mafft.cbrc.jp/alignment/software/license.txt>). MAFFT is not
used by anything in this repository and is not redistributed here.

### MHCflurry 2.0.0 and 2.3.0 — OpenVax

| | |
|---|---|
| Licence | Apache License 2.0 — verified 2026-10-07 at `raw.githubusercontent.com/openvax/mhcflurry/master/LICENSE` |
| Grant | Permissive; permits use, modification and redistribution of software and output, with attribution and notice preservation |
| Restrictions relevant here | None. No academic-only clause, no benchmark-publication clause |
| In this repository | `results/predictors/mhcflurry_2_0_0_test_scores.csv`, `..._2_3_0_test_scores.csv`, the MHCflurry rows of the comparison and contamination artifacts, and `data/derived/TEST_PREDICTOR_OVERLAP_MHCflurry_*.csv` |
| Not in this repository | The package; its model weights and curated training corpora (`data/raw/S6/`, gitignored, Apache-2.0) |

According to PubMed: O'Donnell TJ, Rubinsteyn A, Laserson U. *MHCflurry 2.0:
Improved Pan-Allele Prediction of MHC Class I-Presented Peptides by
Incorporating Antigen Processing.* Cell Systems 2020;11(1):42–48.e7.
[DOI 10.1016/j.cels.2020.06.010](https://doi.org/10.1016/j.cels.2020.06.010) ·
PMID 32711842.

---

## 3. Data

### PXD024871 — PRIDE Archive (the subject of this work)

The deposit is public. This repository contains peptide sequences and
per-acquisition metadata derived from it, not the acquisition files themselves
(tens of gigabytes; `data/raw/**` is gitignored, with provenance records and
SHA-256 digests committed in their place). `DATA_SOURCES.md` records the twelve
provenance fields for each source.

The peptides come from peripheral blood mononuclear cells of 52 chronic
lymphocytic leukaemia participants, identified in the deposit only as UPN01–
UPN58. Those identifiers, the HLA genotypes and the peptide sequences are
reproduced here **as the public deposit publishes them**; this repository adds
no identifying information and attempts no re-identification. Users of HLA
genotype and immunopeptidome data should note that both are in principle
individually distinguishing even without a name attached, and should treat them
with the care that implies.

### UniProt human reference proteome (UP000005640)

Used for the negative construction. Licensed CC BY 4.0, as recorded in
`data/raw/S5/provenance.jsonl`. The payload is gitignored; its URL, release and
SHA-256 are committed.

---

## 4. Libraries

`requirements.txt` pins what the analysis imports. PyTorch (BSD-3-Clause),
NumPy and SciPy (BSD-3-Clause) are the substantive ones; everything else is the
Python standard library. None is vendored into this repository.

---

## 5. If you believe this file is wrong

Open an issue. A licence misreading here is a real problem, not a cosmetic one,
and a correction is more welcome than a quiet fork.
