# FINAL FREEZE  (fourth anchor — nine documents untracked)

```
PXD024871 CNN experiment — public-release freeze

Every gate is closed. The endpoint was read once, under a rule fixed before
any model existed, and is not reopened by this record. NO NUMBER CHANGED IN
THIS FREEZE.

SUPERSEDES the third anchor, which superseded 21048535 and b83a741b. This
re-freeze was opened under D038: nine internal and working documents were
untracked at the project owner's instruction. It changes what the repository
CONTAINS, not what it found. NOTE that untracking does not remove those
documents from this repository's history -- D038 section 2 states the
limitation in full -- and that REPORT.md's removal does NOT hold the findings
back, because DECISION_LOG.md, README.md, this file and results/ still carry
them. D038 section 3 says so.

files         361 tracked (freeze_manifest.json excluded: it cannot hash itself)
bytes         see freeze_manifest.json -> total_bytes
frozen        see freeze_manifest.json -> frozen_utc
parent        see freeze_manifest.json -> parent_commit
branch        claude/mapping-research-project-prompt-glsess
```

**The anchor is the commit that adds `freeze_manifest.json`, not its parent.**
A manifest cannot contain the hash of the commit that carries it. This record
no longer quotes the parent commit or the byte total either, for the same
reason in miniature: the previous version hard-coded both, which forced this
file to be edited after the manifest walk and made the manifest stale for it.
The manifest is the single source for all four values, and this file points at
it instead of duplicating it.

## What changed in this freeze, and what did not

**Changed in THIS freeze (D038):** nine documents untracked at the project
owner's instruction — `METHODOLOGY.md`, `REPORT.md`, `RUN_LOG.md`,
`SECTIONS.md`, `THIRD_PARTY_NOTICES.md`, `POWER_ANALYSIS.md`,
`PROJECT_PROMPT.md`, `HANDOVER.md`, `ENVIRONMENT.md`. All nine remain on disk
and in history. `README.md` gained a section naming them, and the pointers in
`LICENSE`, `LICENSE-docs` and `README.md` to the now-untracked notices file were
repaired. The items below this line were the THIRD anchor's changes and are kept
for the record.

**Did not change:** every result. `POSITIVES.csv`, `NEGATIVES.csv` and
`SPLIT.csv` carry the same digests they have had since `f7550f54`, and all 44
headline numbers still match their artifacts verbatim.

**Changed — withheld (D037):** the T-A4 experiment proposal, replaced by a
provenance stub carrying its SHA-256; 37 MB of verbatim NetMHCpan and
MixMHCpred stdout; two byte-identical duplicate overlap tables. Nothing was
deleted from disk; all three are gitignored with the reason stated inline.

**Changed — added:** `README.md`, `LICENSE` (MIT), `LICENSE-docs` (CC BY 4.0,
legal code retrieved verbatim, not written from memory), `CITATION.cff`,
`THIRD_PARTY_NOTICES.md`, `.gitattributes`.

**Changed — fixed:** `.gitattributes` set `* -text` after the first draft's
`* text=auto eol=lf` was caught; 67 derived tables are genuinely CRLF, and
converting them on checkout would have failed `--verify` on every clone while
passing here. `FILE_MAP_REJECTS.csv` grew the header it never had, and
`phase_a_mapping.py` was fixed at the source so a re-run reproduces it.

**Changed — closed:** `DATA_SOURCES.md` S7 moved from `PENDING` to
`IDENTIFIED, NOT RETRIEVED` — the dataset publication was found while verifying
citations. The cross-check it exists to provide has still not been performed,
and the entry says so.

## What the freeze asserts

`scripts/freeze.py --write` refuses to write the manifest unless
`scripts/freeze.py --verify` passes first, so this record exists only because
all nine checks were clean at the moment it was written:

| # | Check | Result |
|---|---|---|
| 1 | Working tree clean, nothing untracked | pass |
| 2 | Preregistration checksums still hold — the dataset and split have not moved since `f7550f54` (D009) | 6 artifacts, all unchanged |
| 3 | Every artifact, script and figure `REPORT.md` names resolves | pass |
| 4 | Every headline number in `REPORT.md` appears verbatim in the artifact it came from | **44 numbers** |
| 5 | The figures regenerate byte-identically from those artifacts | 7 figures |
| 6 | Every QC gate passed or carries a recorded unavailability | G1–G13, FINAL |
| 7 | Every decision resolved, none left OPEN | D001–D038 |
| 8 | An existing manifest still agrees with the tree, and declares its own exclusion | 361 entries |
| 9 | The trainer's own selftest passes | encoder, AP, gradients, overfit |

Anyone can re-run `python3 scripts/freeze.py --verify` against this tree and get
the same nine blocks. That is what the freeze is for: not that the files have
hashes, but that the hashes were taken of a tree that had been checked.

**Verify it on a fresh clone, not only in place.** That is the lesson of the
`.gitattributes` defect above, and the third instance of the same failure mode
in this project after `TEST_LEAKFREE` and D029/D030: a check that passes locally
for a reason that does not travel.

## The results this freezes

| | Value | Interval |
|---|---|---|
| **Primary endpoint** (read once) | **0.7551** | CI99 [0.7368, 0.7721] vs threshold 0.647 |
| Leakage-free subset | 0.7056 | CI99 [0.6926, 0.7184] |
| Cross-platform, LTQ → Lumos | 0.6959 | does not collapse |
| Cross-platform, Lumos → LTQ | 0.7108 | platform costs 0.04–0.06 AP |
| Allele-specific, HLA-A\*02:01 | +0.0476 | CI99 [+0.0314, +0.0626], 9/9 units |
| Allele-specific, HLA-C\*07:02 | -0.0049 | **not demonstrated** |
| §18 — CNN vs four predictors, common row set | **+0.1373 to +0.1418** | all 10/10 units; the four predictors span only 0.0046 |

## What the freeze does NOT assert

**That the conclusions are right.** It asserts that the tree is internally
consistent and that the numbers in the prose are the numbers in the artifacts.
Those are different claims, and the second is the only one a checksum can carry.

**That the chronology is independently witnessed.** As D009 recorded for the
preregistration, this record is created by the repository owner with the
owner's clock. It fixes ordering *within* the repository and nothing outside it.

**That nothing is left open.** Four things are unavailable rather than done:

- **NetMHCpan 4.2** needs a software licence separate from the 4.1 grant, so its
  training data is registered, it appears in the contamination table, and it is
  scored in no comparison. Its overlap is near-symmetric (20.7% of positives,
  16.2% of negatives), which is the reason that matters more than the licence.
- **§20 robustness across negative-control designs** — the dataset was frozen
  with set C alone.
- **The symmetric allele test** cannot be replicated in this cohort.
- **S4 acquisitions and the S7 cross-check** were never retrieved; S7 is now at
  least identified (D037).

A second cohort is the only route to the middle two, and is the single most
useful thing anyone could add to this work.

**That §20 is safe.** It rests on D032, where a release criterion I had written
was narrowed after it failed and the narrowing was accepted by the project
owner. `REPORT.md` Limitations names this as the report's most reader-dependent
step and states what a reader who rejects it should conclude instead.

**That publishing §18 is cleared.** The NetMHCpan 4.1 academic licence §7(v)
bars publishing benchmark results to third parties without DTU Health Tech's
prior written consent, and §18 is such a benchmark. No consent has been sought.
`THIRD_PARTY_NOTICES.md` §1 and D037 §2 set out the reading, the countervailing
practice, and the options. **This is the one item that a reader of a public
repository should know is unresolved.**

## Selected checksums (SHA-256)

The manifest carries all 361. These are the ones a reader is most likely to want
to check by hand. `FREEZE_RECORD.md` is absent from this list for the same
reason the manifest excludes itself.

```
  124d9ebbf61b19f5acb1dba2fc38ea31e2db24112d5d9247b929187ff5f5ab76  REPORT.md
  5c625b143f3e46cfd07a3d774477e6aeb1a929d6aec35a5b39bbbcfdd3d385fe  DECISION_LOG.md
  12cd5607f0def6b377a3e6576ec5152f20c781da3280c703a829218716333959  DATA_SOURCES.md
  cb3e957e8b61d8509cdaa84590815fdc77112309d40fdd98ecf48028132f0324  PROJECT_PROMPT.md
  78fb6d2771ced5e3052b57c9f14aebbf9dd5438ec52268f15b9905808690e35e  PREREGISTRATION.md
  2d3ecd3827387eeca988aba5a35edd9242942a84f366b1f7691711fa8ef75a98  README.md
  9341941a6252f18f018e5d2a0ffc8acfddbfb14e4207071806f6433fbb1c4c55  LICENSE
  c35d9d8b8bdb44589b37b77d978837d0540211acbd93fd9427f596d7876bbecd  LICENSE-docs
  5591593069557cb775eae8ae787b75371d8beda36e6a314b13a0ebb9f5bec728  CITATION.cff
  6c737a7bb6b9e580c3b85427dcd165b240dc0ebf9d3249c9b8226107363f17b9  data/derived/POSITIVES.csv
  b990aa06ef257a88fc30ef6bdc2cebc25a1f365ded9b71182cd048c7e2438421  data/derived/NEGATIVES.csv
  c60de8a710a554c0e4604e5781a51a191c2d3115330fc463be272a63e3e10415  data/derived/SPLIT.csv
  d4f6edc2ed44781caccbe07dce27db9be75c1999aad25115d0700c1ea8cd18e1  results/model/endpoint.json
  f374e8296261f3697893455ffb5e11be169720c6357c522d75e21471932a3b54  results/qc/predictor_comparison_all.json
```

The first three digests above changed in this freeze; the preregistered three
(`POSITIVES`, `NEGATIVES`, `SPLIT`) did not, and that is the point.

## Verifying this freeze

```
python3 scripts/freeze.py --verify          # re-runs all nine checks
python3 - <<'PYEOF'
import hashlib, json, pathlib
m = json.load(open('freeze_manifest.json'))
bad = [f['path'] for f in m['files']
       if pathlib.Path(f['path']).exists()
       and hashlib.sha256(pathlib.Path(f['path']).read_bytes()).hexdigest() != f['sha256']]
gone = [f['path'] for f in m['files'] if not pathlib.Path(f['path']).exists()]
print('changed since the freeze:', bad or 'nothing')
print('missing since the freeze:', gone or 'nothing')
PYEOF
```

**One file is not covered: `freeze_manifest.json` itself.** A manifest cannot
contain its own digest — hashing it and then overwriting it stores the previous
version's hash. The first attempt at the second freeze did exactly that, and the
verification command printed above caught it on the next run. The manifest now
declares the exclusion in its `excludes` field, and check 8 refuses a manifest
that does not.

No tag was published. One was attempted at the second anchor and the remote
refused it, as it refused the preregistration tag for the same reason (D009);
the commit is the anchor instead, and that is recorded rather than worked around.
