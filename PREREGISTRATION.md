# PREREGISTRATION FREEZE

```
PXD024871 CNN experiment — preregistration freeze

Everything the confirmatory analysis depends on is fixed at this commit:
the dataset, the split, the endpoint reference, and the decisions that
produced them. No model has been fit.

commit        f7550f54045c116a69fa500fb77f8504a7439b5d
dataset       520,000 positives / 520,000 negatives, 52 units
split         10 test units, 5 folds over 42
leakage       15.988% of test positives seen in training
AP floor      0.597 — composition-only, not chance
base seed     20261006

Artifact checksums (SHA-256):
  6c737a7bb6b9e580c3b85427dcd165b240dc0ebf9d3249c9b8226107363f17b9  POSITIVES.csv
  b990aa06ef257a88fc30ef6bdc2cebc25a1f365ded9b71182cd048c7e2438421  NEGATIVES.csv
  c60de8a710a554c0e4604e5781a51a191c2d3115330fc463be272a63e3e10415  SPLIT.csv
  6ffe94e1701d608cd48a914420aeb8148d1f0a34a00cd39a6ec77e959a48ea91  TEST_LEAKFREE.csv
  32f537a030192d21751dc0f65cf729d3e3b11a3adaf764b830fa062c39478afb  FREEZE.json
  23d0ae634aa548ff0d391060fffbfc6b7ff021ae0c23c37fc94b55ae02b6084c  SPLIT_FREEZE.json

Preregistered secondary analyses, fixed before any result exists:
  allele-disjoint split  — 29 test / 23 train units (D001)
  cross-platform transfer — both directions, 25 LTQ / 27 Lumos (D025)
  leakage-free test subset — 84,012 of 100,000 rows (D003)

What this tag proves: these artifacts match this record, and this
ordering within the repository. What it does NOT prove: independent
third-party evidence that this preceded seeing any result. The tag is
made by the repository owner with the owner's clock. See DECISION_LOG D009.
```

## The anchor is this commit, not a tag

**No tag was published.** One was attempted; the session's credential is scoped
to `refs/heads` and the remote refused `refs/tags` with 403. Rather than leave
the freeze depending on a step that had not happened, the anchor is the commit
named above, and this file — committed at it, carrying every artifact checksum —
is the record.

Nothing is lost by that. D009 argued a tag beats a hash in prose because the
document holding the hash is mutable; the same objection applies to a tag, since
both are created by the repository owner with the owner's clock. A tag would
have been a clearer marker, not stronger evidence.

What carries weight is that this file is committed into history. Altering it
later changes every subsequent commit hash, which is detectable by anyone who
recorded the original — and the original is on the remote.

A tag may still be added later without affecting anything here:

```bash
git tag -a preregistration-v1 <commit> -F PREREGISTRATION.md
git push origin preregistration-v1
```

The limit stated in D009 is unchanged either way: this establishes **content
integrity** and **ordering within the repository**, not independent chronology.
Publishing this file's SHA-256 to an external timestamping service would supply
that and would disclose nothing.

## Verifying

```bash
python3 - <<'PY'
import hashlib, pathlib
for f in ['POSITIVES.csv','NEGATIVES.csv','SPLIT.csv','TEST_LEAKFREE.csv',
          'FREEZE.json','SPLIT_FREEZE.json']:
    p = pathlib.Path('data/derived')/f
    print(hashlib.sha256(p.read_bytes()).hexdigest(), f)
PY
```

Any mismatch means the artifact is not the one the preregistration covers, and
nothing downstream may use it.
