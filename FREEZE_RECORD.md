# FINAL FREEZE

```
PXD024871 CNN experiment — final freeze

Every gate is closed. The endpoint was read once, under a rule fixed before
any model existed, and is not reopened by this record.

files         348 tracked
bytes         93,948,128
frozen        2026-10-07T09:50:56Z
branch        claude/mapping-research-project-prompt-glsess
parent        d371a6a6598b058e4a649f356e52cb87e20d9e5f
```

**The anchor is the commit that adds `freeze_manifest.json`, not the parent
above.** A manifest cannot contain the hash of the commit that carries it. The
parent is recorded so the pair is unambiguous: the anchor is the single child of
`d371a6a6598b` that introduces the manifest.

## What the freeze asserts

`scripts/freeze.py --write` refuses to write the manifest unless
`scripts/freeze.py --verify` passes first, so this record exists only because
all eight checks were clean at the moment it was written:

| # | Check | Result |
|---|---|---|
| 1 | Working tree clean, nothing untracked | pass |
| 2 | Preregistration checksums still hold — the dataset and split have not moved since `f7550f54` (D009) | 6 artifacts, all unchanged |
| 3 | Every artifact, script and figure `REPORT.md` names resolves | pass |
| 4 | Every headline number in `REPORT.md` appears verbatim in the artifact it came from | 25 numbers |
| 5 | The figures regenerate byte-identically from those artifacts | 7 figures |
| 6 | Every QC gate passed or carries a recorded unavailability | G1–G13, FINAL |
| 7 | Every decision resolved, none left OPEN | D001–D033 |
| 8 | The trainer's own selftest passes | encoder, AP, gradients, overfit |

Anyone can re-run `python3 scripts/freeze.py --verify` against this tree and get
the same eight lines. That is what the freeze is for: not that the files have
hashes, but that the hashes were taken of a tree that had been checked.

## The results this freezes

| | Value | Interval |
|---|---|---|
| **Primary endpoint** (read once) | **0.7551** | CI99 [0.7368, 0.7721] vs threshold 0.647 |
| Leakage-free subset | 0.7056 | CI99 [0.6926, 0.7184] |
| Cross-platform, LTQ → Lumos | 0.6959 | does not collapse |
| Cross-platform, Lumos → LTQ | 0.7108 | platform costs 0.04–0.06 AP |
| Allele-specific, HLA-A\*02:01 | +0.0476 | CI99 [+0.0314, +0.0626], 9/9 units |
| Allele-specific, HLA-C\*07:02 | -0.0049 | **not demonstrated** |
| CNN vs MHCflurry 2.3.0, mutually naive | +0.1340 | CI99 [+0.1126, +0.1505], 10/10 units |

## What the freeze does NOT assert

**That the conclusions are right.** It asserts that the tree is internally
consistent and that the numbers in the prose are the numbers in the artifacts.
Those are different claims, and the second is the only one a checksum can carry.

**That the chronology is independently witnessed.** As D009 recorded for the
preregistration, this record is created by the repository owner with the
owner's clock. It fixes ordering *within* the repository and nothing outside it.

**That nothing is left open.** Three things are unavailable rather than done,
each recorded in `SECTIONS.md`: §18 lacks NetMHCpan (licence form) and
MixMHCpred (proxy refuses its host); §20 lacks robustness across negative-control
designs (the dataset was frozen with set C alone); and the symmetric allele test
cannot be replicated in this cohort. A second cohort is the only route to the
last two.

**That §20 is safe.** It rests on D032, where a release criterion I had written
was narrowed after it failed and the narrowing was accepted by the project
owner. `REPORT.md` Limitations names this as the report's most reader-dependent
step and states what a reader who rejects it should conclude instead.

## Selected checksums (SHA-256)

The manifest carries all 348. These are the ones a reader is most
likely to want to check by hand:

```
  1488078d6ac7cd7f994870de3811e7ab88bb25eaaf34fb88b7ba3589357999ce  REPORT.md
  96a76da8974943563179c17e3b62103b147a46b25430440787f42c46f21564e9  DECISION_LOG.md
  07a3733e21b756df5144c2c6bc7bf0619163ec6cd8f598a09ac8e65c1eb691da  SECTIONS.md
  ad8d8bcac22754455ea2407a860a8d4d6a4f23556bca691ae30399b5886debdb  METHODOLOGY.md
  a5d594d686b5fa51b8263ba14df720155fea28b9c36de90dfda3f5c2e5ef02cb  DATA_SOURCES.md
  cb3e957e8b61d8509cdaa84590815fdc77112309d40fdd98ecf48028132f0324  PROJECT_PROMPT.md
  78fb6d2771ced5e3052b57c9f14aebbf9dd5438ec52268f15b9905808690e35e  PREREGISTRATION.md
  6c737a7bb6b9e580c3b85427dcd165b240dc0ebf9d3249c9b8226107363f17b9  data/derived/POSITIVES.csv
  b990aa06ef257a88fc30ef6bdc2cebc25a1f365ded9b71182cd048c7e2438421  data/derived/NEGATIVES.csv
  c60de8a710a554c0e4604e5781a51a191c2d3115330fc463be272a63e3e10415  data/derived/SPLIT.csv
  d4f6edc2ed44781caccbe07dce27db9be75c1999aad25115d0700c1ea8cd18e1  results/model/endpoint.json
  77284796784d9a9a81ef9ad2f361edba9e15936b418a322da253802456c52c9e  results/model/multi_allele.json
  3bcb6710b9fec5d1ffb0358e1b13e8f3e6415c2a67bff64afc63ffee527ca4f7  results/qc/predictor_comparison.json
```

## Verifying this freeze

```
python3 scripts/freeze.py --verify          # re-runs all eight checks
python3 - <<'EOF'
import hashlib, json, pathlib
m = json.load(open('freeze_manifest.json'))
bad = [f['path'] for f in m['files']
       if pathlib.Path(f['path']).exists()
       and hashlib.sha256(pathlib.Path(f['path']).read_bytes()).hexdigest() != f['sha256']]
print('changed since the freeze:', bad or 'nothing')
EOF
```

No tag was published. One was attempted and the remote refused it, as it
refused the preregistration tag for the same reason (D009); the commit is the
anchor instead, and that is recorded rather than worked around.
